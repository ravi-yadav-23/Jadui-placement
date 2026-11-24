"""Resume text -> ResumeProfile, with every LLM claim checked against the original text.

  1. The LLM returns a ProfileDraft (it only sees the REDACTED text).
  2. We give every bullet a stable ID: "exp0.b1" = experience entry 0, bullet 1.
  3. Grounding: each bullet must actually appear in the resume. Extraction LLMs sometimes
     "improve" or invent bullets; those get grounded=False and are excluded from scoring.
  4. Numbers the LLM read (CGPA, graduation year) must appear in the text, else they're dropped.
"""

import re

from rapidfuzz import fuzz

from app.llm.client import LLMClient
from app.resume.pipeline.redact import redact
from app.resume.schemas import Bullet, Contacts, EntryDraft, ProfileDraft, ResumeProfile

MAX_LLM_CHARS = 12_000
GROUNDING_THRESHOLD = 90  # rapidfuzz partial_ratio, 0-100


def normalize(text: str) -> str:
    """Lowercase, re-join hyphenated line breaks, unify quotes/dashes, collapse whitespace."""
    text = re.sub(r"-\n(?=[a-z])", "", text)                 # "inter-\nception" -> "interception"
    text = text.translate(str.maketrans("‘’“”–—•", "''\"\"--*"))
    return re.sub(r"\s+", " ", text).strip().lower()


def is_grounded(bullet: str, normalized_source: str) -> bool:
    needle = normalize(bullet)
    if not needle:
        return False
    if needle in normalized_source:
        return True
    if len(needle) < 20:  # short strings fuzzy-match almost anything, so they must match exactly
        return False
    return fuzz.partial_ratio(needle, normalized_source) >= GROUNDING_THRESHOLD


def _bullets(prefix: str, texts: list[str], source: str) -> list[Bullet]:
    return [Bullet(id=f"{prefix}.b{i}", text=t.strip(), grounded=is_grounded(t, source))
            for i, t in enumerate(texts) if t.strip()]


def _entries(prefix: str, drafts: list[EntryDraft], source: str) -> list[dict]:
    return [
        {**draft.model_dump(exclude={"bullets"}), "id": f"{prefix}{i}",
         "bullets": _bullets(f"{prefix}{i}", draft.bullets, source)}
        for i, draft in enumerate(drafts)
    ]


def build_profile(draft: ProfileDraft, raw_text: str) -> ResumeProfile:
    source = normalize(raw_text)
    education = []
    for edu in draft.education:
        if edu.cgpa is not None and not _number_in_text(edu.cgpa, raw_text):
            edu.cgpa, edu.cgpa_scale = None, None
        if edu.grad_year is not None and str(edu.grad_year) not in raw_text:
            edu.grad_year = None
        education.append(edu)

    return ResumeProfile(
        headline=draft.headline,
        summary=draft.summary,
        location=draft.location,
        education=education,
        experience=_entries("exp", draft.experience, source),
        projects=_entries("proj", draft.projects, source),
        skills=_dedupe(draft.skills),
        certifications=draft.certifications,
        achievements=_bullets("ach", draft.achievements, source),
    )


def _number_in_text(value: float, text: str) -> bool:
    as_text = f"{value:g}"                       # 8.4 -> "8.4", 9.0 -> "9"
    return re.search(rf"(?<![\d.]){re.escape(as_text)}(?![\d])", text) is not None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in (i.strip() for i in items):
        if item and item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result


def structure_resume(llm: LLMClient, raw_text: str, contacts: Contacts) -> ResumeProfile:
    safe_text = redact(raw_text, contacts)[:MAX_LLM_CHARS]
    draft = llm.structured("resume_structure", ProfileDraft, {"resume_text": safe_text})
    return build_profile(draft, raw_text)


def reassign_ids(profile: ResumeProfile) -> ResumeProfile:
    """After a user edit: keep the user's content, make IDs consistent, trust every bullet.

    The user is the source of truth about their own resume, so edited bullets count as grounded.
    """
    data = profile.model_dump()
    for key, prefix in (("experience", "exp"), ("projects", "proj")):
        for i, entry in enumerate(data[key]):
            entry["id"] = f"{prefix}{i}"
            entry["bullets"] = [{"id": f"{prefix}{i}.b{j}", "text": b["text"], "grounded": True}
                                for j, b in enumerate(entry["bullets"]) if b["text"].strip()]
    data["achievements"] = [{"id": f"ach.b{j}", "text": b["text"], "grounded": True}
                            for j, b in enumerate(data["achievements"]) if b["text"].strip()]
    return ResumeProfile.model_validate(data)
