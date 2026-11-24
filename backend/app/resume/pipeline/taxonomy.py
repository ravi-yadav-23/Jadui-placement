"""Skill normalisation: "postgres", "PostgreSQL", "psql" all mean the canonical "PostgreSQL".

Used by the truth guard (did a rewrite add a technology?) and by JD matching
(does the resume have the skill the JD asks for?).
"""

import re
from functools import lru_cache
from pathlib import Path

import yaml

TAXONOMY_FILE = Path(__file__).parent.parent / "data" / "skills_taxonomy.yaml"

# Concrete tools/technologies. Concepts (fundamentals, process) like "caching" or "agile"
# are excluded when the truth guard checks for added technologies.
TECH_CATEGORIES = {"language", "backend", "frontend", "database", "devops", "cloud", "testing", "ai", "data"}


@lru_cache(maxsize=1)
def _taxonomy() -> tuple[dict[str, str], dict[str, str]]:
    """Returns (alias -> canonical, canonical -> category)."""
    raw = yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8"))
    aliases: dict[str, str] = {}
    categories: dict[str, str] = {}
    for name, info in raw.items():
        canonical_name = str(name)
        categories[canonical_name] = info.get("category", "other")
        # Very short names ("C", "Go") are ordinary words/letters; only match them via explicit aliases.
        if len(canonical_name) > 2:
            aliases[canonical_name.lower()] = canonical_name
        for alias in info.get("aliases", []):
            aliases[str(alias).lower()] = canonical_name
    return aliases, categories


@lru_cache(maxsize=1)
def _pattern() -> re.Pattern:
    # Longest aliases first, so "spring boot" wins over "spring" and "next.js" over "next".
    aliases = sorted(_taxonomy()[0], key=len, reverse=True)
    alternation = "|".join(re.escape(a) for a in aliases)
    # Whole-word match that also works for "c++", "c#", "node.js": no word char / + / # around it.
    return re.compile(rf"(?<![\w+#./-])(?:{alternation})(?![\w+#]|\.\w)", re.IGNORECASE)


def canonical(name: str) -> str | None:
    """'postgres' -> 'PostgreSQL'; unknown names -> None."""
    return _taxonomy()[0].get(name.strip().lower())


def find_skills(text: str, tech_only: bool = False) -> set[str]:
    """All canonical skills mentioned in the text (optionally only concrete technologies)."""
    aliases, categories = _taxonomy()
    found = {aliases[m.group(0).lower()] for m in _pattern().finditer(text)}
    if tech_only:
        found = {s for s in found if categories.get(s) in TECH_CATEGORIES}
    return found


@lru_cache(maxsize=1)
def _implications() -> dict[str, list[str]]:
    raw = yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8"))
    return {str(name): [str(s) for s in info.get("implies", [])] for name, info in raw.items()}


def with_implied(skills: set[str]) -> set[str]:
    """Add skills that are implied by others: {"Next.js"} -> {"Next.js", "React", "JavaScript"}."""
    result = set(skills)
    frontier = list(skills)
    while frontier:  # follow chains like Next.js -> React -> JavaScript
        for implied in _implications().get(frontier.pop(), []):
            if implied not in result:
                result.add(implied)
                frontier.append(implied)
    return result


def normalize_skill(name: str) -> str:
    """Canonical name if we know it, otherwise the cleaned original (unknown skills still work)."""
    return canonical(name) or name.strip()
