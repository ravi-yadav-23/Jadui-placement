import pytest
from pydantic import BaseModel

from app.core.db import InMemoryDatabase
from app.core.errors import AppError
from app.llm import client as llm_client
from app.llm.client import LLMClient
from app.llm.providers import FakeProvider, LLMProviderError, TransientLLMError


class Answer(BaseModel):
    score: int
    label: str


@pytest.fixture(autouse=True)
def echo_prompt(tmp_path, monkeypatch):
    (tmp_path / "echo.v1.md").write_text("Say something about $topic", encoding="utf-8")
    monkeypatch.setattr(llm_client, "PROMPTS_DIR", tmp_path)
    monkeypatch.setitem(llm_client.PROMPT_VERSIONS, "echo", "v1")
    # Skip tenacity's back-off sleep so retry tests are instant.
    monkeypatch.setattr(LLMClient._ask.retry, "sleep", lambda _: None)


def scripted(*answers):
    """A provider that returns the given answers in order (dict, str or an exception)."""
    queue = list(answers)

    def responder(_name, _prompt):
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return FakeProvider(responder)


def test_valid_answer_is_returned_as_model():
    llm = LLMClient([scripted({"score": 7, "label": "ok"})])
    assert llm.structured("echo", Answer, {"topic": "x"}) == Answer(score=7, label="ok")


def test_invalid_json_gets_one_repair_attempt():
    provider = scripted({"score": "not-a-number"}, {"score": 3, "label": "fixed"})
    llm = LLMClient([provider])
    assert llm.structured("echo", Answer, {"topic": "x"}).label == "fixed"
    assert provider.calls == ["echo", "echo"]


def test_falls_back_to_next_provider_after_two_invalid_answers():
    bad = scripted({"nope": 1}, {"still": "bad"})
    good = scripted({"score": 9, "label": "fallback"})
    llm = LLMClient([bad, good])
    assert llm.structured("echo", Answer, {"topic": "x"}).label == "fallback"
    assert llm.last_model == good.model


def test_transient_error_is_retried_on_same_provider():
    provider = scripted(TransientLLMError("timeout"), {"score": 1, "label": "after-retry"})
    llm = LLMClient([provider])
    assert llm.structured("echo", Answer, {"topic": "x"}).label == "after-retry"


def test_all_providers_failing_raises_503():
    llm = LLMClient([scripted(LLMProviderError("bad key"))])
    with pytest.raises(AppError) as err:
        llm.structured("echo", Answer, {"topic": "x"})
    assert err.value.status == 503


def test_every_attempt_is_logged_without_prompt_text():
    db = InMemoryDatabase()
    llm = LLMClient([scripted(TransientLLMError("t"), {"score": 1, "label": "a"})], db, "user-a")
    llm.structured("echo", Answer, {"topic": "secret resume text"})
    rows = db.logs["llm_calls"]
    assert [r["ok"] for r in rows] == [False, True]
    assert all("secret" not in str(r) for r in rows)
    assert rows[1]["prompt_version"] == "v1" and rows[1]["user_id"] == "user-a"
