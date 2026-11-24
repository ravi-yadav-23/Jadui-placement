"""The one way the app talks to an LLM.

    llm = get_llm(db, user_id)
    profile = llm.structured("resume_structure", ResumeProfile, {"resume_text": text})

What `structured()` guarantees:
  1. The prompt comes from a versioned file (prompts/<name>.<version>.md), so every
     stored result records exactly which prompt produced it.
  2. The answer is validated against a Pydantic model. If validation fails, we retry ONCE
     with the validation error appended (models usually fix their own JSON).
  3. Timeouts / 429 / 5xx are retried once on the same provider, then we fall back
     to the next provider (Gemini -> Groq).
  4. Every attempt is logged to `llm_calls` (tokens, latency, ok/error) - never the prompt text.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from string import Template
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.db import Database
from app.core.errors import AppError
from app.llm.providers import FakeProvider, GeminiProvider, GroqProvider, LLMProviderError, TransientLLMError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Bump a version when you change a prompt; old analyses keep the version they were made with.
PROMPT_VERSIONS: dict[str, str] = {
    "resume_structure": "v1",
    "resume_review": "v1",
    "jd_parse": "v1",
    "jd_match": "v1",
    "interview_plan": "v1",
    "interview_judge": "v1",
    "planner_summary": "v1",
    "planner_projects": "v1",
    "coach": "v1",
}


def render_prompt(name: str, variables: dict[str, str]) -> str:
    path = PROMPTS_DIR / f"{name}.{PROMPT_VERSIONS[name]}.md"
    return Template(path.read_text(encoding="utf-8")).substitute(variables)


class LLMClient:
    def __init__(self, providers: list, db: Database | None = None, user_id: str | None = None):
        self.providers = providers
        self.db = db
        self.user_id = user_id
        self.last_model: str | None = None  # which model actually answered (stored on the analysis)

    def structured(self, prompt_name: str, schema: type[T], variables: dict[str, str], temperature: float = 0.0) -> T:
        prompt = render_prompt(prompt_name, variables)
        for provider in self.providers:
            try:
                result = self._ask_and_validate(provider, prompt, schema, temperature, prompt_name)
                self.last_model = provider.model
                return result
            except (LLMProviderError, TransientLLMError, ValidationError) as exc:
                log.warning("LLM provider %s failed for %s: %s", provider.name, prompt_name, exc)
        raise AppError("llm_unavailable", "The AI service is unavailable right now. Please try again.", 503)

    def _ask_and_validate(self, provider, prompt: str, schema: type[T], temperature: float, prompt_name: str) -> T:
        text = self._ask(provider, prompt, schema, temperature, prompt_name)
        try:
            return schema.model_validate_json(text)
        except ValidationError as first_error:
            repair = (
                f"{prompt}\n\nYour previous answer was not valid for the required JSON schema.\n"
                f"Validation errors:\n{first_error}\nReturn corrected JSON only."
            )
            text = self._ask(provider, repair, schema, temperature, prompt_name)
            return schema.model_validate_json(text)  # a second failure propagates -> next provider

    @retry(
        retry=retry_if_exception_type(TransientLLMError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(min=1, max=4),
        reraise=True,
    )
    def _ask(self, provider, prompt: str, schema: type[BaseModel], temperature: float, prompt_name: str) -> str:
        start = time.perf_counter()
        try:
            result = provider.generate_json(prompt, schema, temperature, prompt_name)
        except Exception as exc:
            self._log_call(provider, prompt_name, start, ok=False, error=type(exc).__name__)
            raise
        self._log_call(provider, prompt_name, start, ok=True, tokens=(result.input_tokens, result.output_tokens))
        return result.text

    def _log_call(self, provider, prompt_name, start, ok, error=None, tokens=(None, None)) -> None:
        if self.db is None:
            return
        try:
            self.db.log("llm_calls", {
                "user_id": self.user_id,
                "purpose": prompt_name,
                "provider": provider.name,
                "model": provider.model,
                "prompt_version": PROMPT_VERSIONS[prompt_name],
                "input_tokens": tokens[0],
                "output_tokens": tokens[1],
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "ok": ok,
                "error": error,
            })
        except Exception:  # logging must never break the request
            log.exception("could not write llm_calls row")


def get_llm(db: Database | None, user_id: str | None) -> LLMClient:
    if settings.LLM_PROVIDER == "fake":
        from app.llm.fake_responses import default_responder

        return LLMClient([FakeProvider(default_responder)], db, user_id)

    providers = []
    timeout = settings.LLM_TIMEOUT_SECONDS
    if settings.GEMINI_API_KEY:
        providers.append(GeminiProvider(settings.GEMINI_API_KEY, settings.LLM_PRIMARY_MODEL, timeout))
    if settings.GROQ_API_KEY:
        providers.append(GroqProvider(settings.GROQ_API_KEY, settings.LLM_FALLBACK_MODEL, timeout))
    if not providers:
        raise AppError("llm_not_configured", "No LLM API key configured on the server", 500)
    return LLMClient(providers, db, user_id)
