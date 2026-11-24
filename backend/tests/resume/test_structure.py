from app.llm.client import LLMClient
from app.llm.providers import FakeProvider
from app.resume.pipeline.contacts import extract_contacts
from app.resume.pipeline.redact import redact
from app.resume.pipeline.structure import build_profile, is_grounded, normalize, structure_resume
from app.resume.schemas import ProfileDraft
from tests.resume import builders
from tests.resume.builders import SAMPLE_RESUME
from tests.resume.conftest import auth

CONTACTS = extract_contacts(SAMPLE_RESUME, [])


def test_redaction_removes_name_and_contacts():
    safe = redact(SAMPLE_RESUME, CONTACTS)
    for secret in ("Asha Verma", "asha.verma@example.com", "98765 43210", "linkedin.com/in/ashaverma"):
        assert secret not in safe
    assert safe.startswith("[NAME]\n[EMAIL] | [PHONE] | [LINKEDIN] | [GITHUB]")
    assert "Built a FastAPI service" in safe  # content is untouched


def test_grounding_accepts_verbatim_wrapped_and_hyphenated_bullets():
    source = normalize("• Automated course data collection, maintaining\na MySQL backend with network inter-\nception")
    assert is_grounded("Automated course data collection, maintaining a MySQL backend", source)
    assert is_grounded("a MySQL backend with network interception", source)


def test_grounding_rejects_invented_bullets():
    source = normalize(SAMPLE_RESUME)
    assert not is_grounded("Led a team of 12 engineers to migrate the platform to Kubernetes", source)
    assert not is_grounded("Built APIs", source)  # short text must match exactly


def test_numbers_not_in_the_text_are_dropped():
    draft = ProfileDraft.model_validate({"education": [
        {"institution": "Example Institute", "grad_year": 2026, "cgpa": 9.1, "cgpa_scale": 10}]})
    edu = build_profile(draft, SAMPLE_RESUME).education[0]
    assert edu.grad_year == 2026      # "2026" is in the resume
    assert edu.cgpa is None           # 9.1 is not (the resume says 8.4)


def test_llm_only_sees_redacted_text_and_gets_ids_assigned():
    seen_prompts = []

    def responder(_name, prompt):
        seen_prompts.append(prompt)
        return {"experience": [{"title": "Backend Intern", "org": "Acme Payments", "bullets": [
            "Built a FastAPI service for invoice reconciliation handling 20k requests per day",
            "Reduced cloud costs by 60% across 4 regions"]}]}

    profile = structure_resume(LLMClient([FakeProvider(responder)]), SAMPLE_RESUME, CONTACTS)
    assert "asha.verma@example.com" not in seen_prompts[0] and "Asha Verma" not in seen_prompts[0]
    bullets = profile.experience[0].bullets
    assert [b.id for b in bullets] == ["exp0.b0", "exp0.b1"]
    assert [b.grounded for b in bullets] == [True, False]  # the second bullet was invented


def upload_ready(client) -> dict:
    resume_id = client.post("/api/v2/resumes", files={"file": ("Asha_Verma.pdf", builders.single_column_pdf())},
                            headers=auth()).json()["id"]
    return client.get(f"/api/v2/resumes/{resume_id}", headers=auth()).json()


def test_upload_produces_a_profile(client):
    detail = upload_ready(client)
    assert detail["status"] == "ready"
    profile = detail["profile"]
    assert profile["experience"][0]["bullets"][0]["id"] == "exp0.b0"
    assert "FastAPI" in profile["skills"]
    assert profile["education"][0]["cgpa"] == 8.4


def test_user_can_correct_the_profile(client):
    detail = upload_ready(client)
    profile = detail["profile"]
    profile["projects"][0]["bullets"].append({"id": "anything", "text": "Added CSV export used by 3 colleges"})
    resp = client.patch(f"/api/v2/resumes/{detail['id']}/profile", json=profile, headers=auth())
    assert resp.status_code == 200
    saved = resp.json()
    assert saved["profile_edited"] is True
    assert [b["id"] for b in saved["profile"]["projects"][0]["bullets"]][-1] == "proj0.b2"


def test_llm_outage_fails_the_resume_but_keeps_the_checks(client, monkeypatch):
    from app.core.errors import AppError
    from app.resume import service

    def broken(*_args, **_kwargs):
        raise AppError("llm_unavailable", "The AI service is unavailable right now.", 503)

    monkeypatch.setattr(service, "structure_resume", broken)
    detail = upload_ready(client)
    assert detail["status"] == "failed"
    assert detail["error"].startswith("The AI service is unavailable")
    assert detail["checks"]  # parse health is still shown
