"""Canned LLM answers used when LLM_PROVIDER=fake (unit tests and the Playwright E2E run).

They are realistic enough for the UI to render every section, and deterministic,
so E2E assertions never flake. Real behaviour is measured by the eval suite instead.
"""


def default_responder(prompt_name: str, prompt: str) -> dict:
    handler = _HANDLERS.get(prompt_name)
    if handler is None:
        raise KeyError(f"No fake response registered for prompt '{prompt_name}'")
    return handler(prompt)


_HANDLERS: dict = {}
