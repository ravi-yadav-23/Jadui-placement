"""Contact details by regex: deterministic, instant, and keeps personal data away from the LLM."""

import re

from app.resume.schemas import Contacts

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# A run of digits/spaces/dashes/brackets with an optional +country code, checked for 10-13 digits below.
PHONE = re.compile(r"\+?\d[\d\s().-]{8,16}\d")
LINKEDIN = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w%-]+/?", re.IGNORECASE)
GITHUB = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+", re.IGNORECASE)
LEETCODE = re.compile(r"(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?[\w-]+/?", re.IGNORECASE)
# Portfolio: an explicit http(s) URL, or a bare domain on a typical portfolio host.
PORTFOLIO = re.compile(
    r"https?://[^\s|,]+|\b[\w-]+(?:\.[\w-]+)*\.(?:vercel\.app|netlify\.app|github\.io|dev|me)\b(?:/[^\s|,]*)?",
    re.IGNORECASE,
)
KNOWN_HOSTS = ("linkedin.com", "github.com", "leetcode.com", "mailto:")


def _first(pattern: re.Pattern, *sources: str) -> str | None:
    for source in sources:
        match = pattern.search(source)
        if match:
            return match.group(0).rstrip("/.")
    return None


def _phone(text: str) -> str | None:
    for match in PHONE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if 10 <= len(digits) <= 13:
            return match.group(0).strip()
    return None


def _portfolio(source: str) -> str | None:
    for match in PORTFOLIO.finditer(source):
        value = match.group(0)
        after_at = match.start() > 0 and source[match.start() - 1] == "@"  # the domain of an email
        if not after_at and not any(host in value.lower() for host in KNOWN_HOSTS):
            return value.rstrip("/.")
    return None


def extract_contacts(text: str, links: list[str]) -> Contacts:
    """Visible text wins; hyperlink targets are a fallback (see the `hyperlink_only` check)."""
    link_text = "\n".join(links)
    # Portfolio from visible text only: hyperlinks also include project/demo links.
    portfolio = _portfolio(text)
    return Contacts(
        email=_first(EMAIL, text, link_text.replace("mailto:", "")),
        phone=_phone(text),
        linkedin=_first(LINKEDIN, text, link_text),
        github=_first(GITHUB, text, link_text),
        leetcode=_first(LEETCODE, text, link_text),
        portfolio=portfolio,
    )


def visible_in_text(value: str, text: str) -> bool:
    """Is a link (e.g. 'https://github.com/x') visible in the text, ignoring the scheme/www?"""
    core = re.sub(r"^(?:https?://)?(?:www\.)?", "", value).lower()
    return core in text.lower()
