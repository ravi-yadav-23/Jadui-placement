"""Remove personal identifiers before any text is sent to an LLM.

Why: research on AI resume screening found strong bias based on names (a proxy for
race and gender). The LLM never needs the name or contact details to judge the content,
and we already extracted contacts with regex, so we replace them with neutral tokens.
"""

import re

from app.resume.schemas import Contacts

MAX_NAME_WORDS = 4


def redact(text: str, contacts: Contacts) -> str:
    redacted = text
    tokens = {
        "email": "[EMAIL]", "phone": "[PHONE]", "linkedin": "[LINKEDIN]",
        "github": "[GITHUB]", "leetcode": "[LEETCODE]", "portfolio": "[PORTFOLIO]",
    }
    for field, token in tokens.items():
        value = getattr(contacts, field)
        if value:
            redacted = redacted.replace(value, token)
    redacted = _redact_name(redacted)
    return redacted


def _redact_name(text: str) -> str:
    """A resume's first non-empty line is almost always the candidate's name."""
    first_line = next((line.strip() for line in text.split("\n") if line.strip()), "")
    words = first_line.split()
    looks_like_name = 0 < len(words) <= MAX_NAME_WORDS and all(re.fullmatch(r"[A-Za-z.'-]+", w) for w in words)
    if not looks_like_name:
        return text
    return text.replace(first_line, "[NAME]")  # also catches the name repeated elsewhere
