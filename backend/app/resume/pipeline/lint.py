"""Deterministic bullet rules. Everything here is counted by code, not judged by an LLM,
so it is instant, free, and gives the same answer every time.
"""

import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import yaml

from app.resume.pipeline.taxonomy import find_skills, normalize_skill, with_implied
from app.resume.schemas import Finding, ResumeProfile

WORDS_FILE = Path(__file__).parent.parent / "data" / "lint_words.yaml"
MIN_WORDS, MAX_WORDS = 8, 32       # ~1-2 lines on a one-page resume
MAX_SAME_OPENER = 3

METRIC = re.compile(r"\d")         # any digit: 40%, 20k, 3x, 300 students, 2 weeks
PASSIVE = re.compile(r"\b(?:was|were|is|are|been|being)\s+\w+(?:ed|en)\b", re.IGNORECASE)
PRONOUN = re.compile(r"\bI\b|\b(?:me|my|we|our)\b", re.IGNORECASE)


@lru_cache(maxsize=1)
def words() -> dict[str, list[str]]:
    return yaml.safe_load(WORDS_FILE.read_text(encoding="utf-8"))


def first_word(text: str) -> str:
    match = re.match(r"\W*([A-Za-z-]+)", text)
    return match.group(1).lower() if match else ""


def _has_phrase(text: str, phrases: list[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(p)}\b", low) for p in phrases)


def lint_bullet(text: str) -> list[str]:
    """Return issue codes for one bullet."""
    issues = []
    lexicon = words()
    opener = first_word(text)
    if not METRIC.search(text):
        issues.append("no_metric")
    weak_opening = any(text.lower().lstrip("•-* ").startswith(p) for p in lexicon["weak_openers"])
    strong_verb = opener in lexicon["action_verbs"] or (opener.endswith("ed") and len(opener) > 4)
    if weak_opening or not strong_verb:
        issues.append("weak_start")
    if PRONOUN.search(text):
        issues.append("pronoun")
    if PASSIVE.search(text):
        issues.append("passive")
    if not MIN_WORDS <= len(text.split()) <= MAX_WORDS:
        issues.append("length")
    if _has_phrase(text, lexicon["buzzwords"]):
        issues.append("buzzword")
    if _has_phrase(text, lexicon["vague_phrases"]):
        issues.append("vague")
    return issues


def lint_resume(profile: ResumeProfile) -> list[Finding]:
    """Rules that look at the resume as a whole."""
    findings: list[Finding] = []
    bullets = [b for b in profile.all_bullets() if b.grounded]

    openers = Counter(first_word(b.text) for b in bullets)
    for verb, count in openers.items():
        if verb and count > MAX_SAME_OPENER:
            findings.append(Finding(code="repeated_verb",
                                    message=f"{count} bullets start with '{verb}'. Vary your verbs."))

    unsupported = unsupported_skills(profile)
    if unsupported:
        findings.append(Finding(
            code="unsupported_skill",
            message=f"Listed but never shown in a bullet or project stack: {', '.join(unsupported)}. "
                    "Show where you used them, or consider dropping them.",
        ))
    return findings


def unsupported_skills(profile: ResumeProfile) -> list[str]:
    """Skills in the Skills section with no evidence anywhere else in the resume."""
    evidence_text = " ".join(
        [b.text for b in profile.all_bullets()]
        + [t for entry in profile.experience + profile.projects for t in entry.tech]
        + [entry.title for entry in profile.projects]
    )
    stack = {normalize_skill(t) for e in profile.experience + profile.projects for t in e.tech}
    evidenced = with_implied(find_skills(evidence_text) | stack)  # FastAPI in a bullet is evidence of Python
    listed = [normalize_skill(s) for s in profile.skills]
    # Only judge concrete technologies: concepts (DSA, OOP) and soft skills aren't expected in bullets.
    return [s for s in dict.fromkeys(listed) if s in find_skills(s, tech_only=True) and s not in evidenced]
