"""LLM providers. Each one does exactly one thing: prompt in -> JSON text out.

Validation, repair and fallback live in client.py, so providers stay small and swappable.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class LLMResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class TransientLLMError(Exception):
    """Timeouts, 429s, 5xx: worth retrying the same provider once."""


class LLMProviderError(Exception):
    """Anything else (bad key, bad request): move on to the next provider."""


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_s: float):
        from google import genai
        from google.genai import types

        self._types = types
        self.model = model
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))

    def generate_json(self, prompt: str, schema: type[BaseModel], temperature: float, prompt_name: str) -> LLMResult:
        from google.genai import errors

        config = self._types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
        )
        try:
            resp = self._client.models.generate_content(model=self.model, contents=prompt, config=config)
        except errors.ServerError as exc:
            raise TransientLLMError(str(exc)) from exc
        except errors.ClientError as exc:
            if getattr(exc, "code", None) == 429:
                raise TransientLLMError(str(exc)) from exc
            raise LLMProviderError(str(exc)) from exc
        except Exception as exc:  # network errors / timeouts from httpx
            raise TransientLLMError(str(exc)) from exc
        usage = resp.usage_metadata
        return LLMResult(
            text=resp.text or "",
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )


class GroqProvider:
    """Groq through its OpenAI-compatible API. Best-effort JSON-schema mode; client.py validates."""

    name = "groq"

    def __init__(self, api_key: str, model: str, timeout_s: float):
        import openai

        self._openai = openai
        self.model = model
        self._client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key, timeout=timeout_s)

    def generate_json(self, prompt: str, schema: type[BaseModel], temperature: float, prompt_name: str) -> LLMResult:
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
                },
            )
        except (self._openai.APITimeoutError, self._openai.APIConnectionError, self._openai.RateLimitError) as exc:
            raise TransientLLMError(str(exc)) from exc
        except self._openai.InternalServerError as exc:
            raise TransientLLMError(str(exc)) from exc
        except self._openai.APIError as exc:
            raise LLMProviderError(str(exc)) from exc
        usage = resp.usage
        return LLMResult(
            text=resp.choices[0].message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )


# A responder gets (prompt_name, rendered prompt) and returns the dict the model "would" return.
Responder = Callable[[str, str], dict]


class FakeProvider:
    """Deterministic provider for tests and the E2E run (LLM_PROVIDER=fake). No network."""

    name = "fake"
    model = "fake-model"

    def __init__(self, responder: Responder):
        self.responder = responder
        self.calls: list[str] = []  # prompt names, so tests can assert what was called

    def generate_json(self, prompt: str, schema: type[BaseModel], temperature: float, prompt_name: str) -> LLMResult:
        self.calls.append(prompt_name)
        payload = self.responder(prompt_name, prompt)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return LLMResult(text=text, input_tokens=len(prompt) // 4, output_tokens=len(text) // 4)
