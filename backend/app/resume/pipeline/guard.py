"""The truth guard: an LLM rewrite may rephrase a bullet, but never add facts.

Rules, applied to every suggested rewrite:
  1. Numbers   - a number not in the original is replaced by the placeholder [X]
                 (the user fills it in, or deletes it). We never let a made-up metric through.
  2. Tech      - a technology not in the original bullet (or that entry's stack) -> rewrite rejected.
  3. Names     - a capitalised name (company, product) not in the original -> rewrite rejected.
  4. Ownership - adding "Led", "Architected", ... when the original didn't claim it -> rejected.

If a rewrite is rejected the user still gets the coach questions, just no rewrite.
"""

import re
from dataclasses import dataclass, field

from app.resume.pipeline.lint import first_word, words
from app.resume.pipeline.taxonomy import find_skills

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
CAPITALISED = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:[.-][A-Za-z0-9]+)*\b")
PLACEHOLDER = "[X]"
# Capitalised words that are not facts (sentence-level words, common acronyms).
NEUTRAL_CAPS = {"x", "api", "apis", "ui", "ux", "db", "the", "a", "an", "and", "for", "with", "to", "in", "of",
                "by", "on", "using", "via", "from", "into"}


@dataclass
class GuardResult:
    text: str | None                       # None = rejected
    notes: list[str] = field(default_factory=list)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in NUMBER.findall(text)}


def guard_rewrite(original: str, rewrite: str | None, allowed_tech: set[str] | None = None) -> GuardResult:
    if not rewrite or not rewrite.strip():
        return GuardResult(None)
    text = rewrite.strip()
    notes: list[str] = []
    allowed_tech = allowed_tech or set()

    # 1. Numbers: keep only numbers that the original already had.
    known = _numbers(original)

    def keep_or_placeholder(match: re.Match) -> str:
        return match.group(0) if match.group(0).replace(",", "") in known else PLACEHOLDER

    replaced = NUMBER.sub(keep_or_placeholder, text)
    if replaced != text:
        notes.append("Replaced a number that isn't in your original bullet with [X]. Fill in the real value.")
        text = replaced

    # 2. Technologies must come from the original bullet or this entry's tech stack.
    added_tech = find_skills(text, tech_only=True) - find_skills(original, tech_only=True) - allowed_tech
    if added_tech:
        return GuardResult(None, [f"Rejected: the rewrite added {', '.join(sorted(added_tech))}."])

    # 3. Capitalised names (companies, products) must already be in the original.
    original_low = original.lower()
    for token in CAPITALISED.findall(text)[1:]:          # skip the first word (sentence case)
        if token.lower() not in NEUTRAL_CAPS and token.lower() not in original_low and not find_skills(token):
            return GuardResult(None, [f"Rejected: the rewrite introduced '{token}', which isn't in the original."])

    # 4. No promotion to leadership/ownership that the original didn't claim.
    inflation = set(words()["inflation_verbs"])
    claims_now = first_word(text) in inflation
    claimed_before = first_word(original) in inflation or any(w in original_low for w in (" led ", "lead", "team"))
    if claims_now and not claimed_before:
        return GuardResult(None, ["Rejected: the rewrite claims leadership the original doesn't mention."])

    return GuardResult(text, notes)
