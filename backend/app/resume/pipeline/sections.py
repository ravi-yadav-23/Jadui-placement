"""Find section headings ("EXPERIENCE", "Technical Skills:", ...) in extracted text.

A line counts as a heading if it is short and its lowercased text is a known alias.
Short ALL-CAPS lines that are NOT known aliases are reported as non-standard headings,
because a parser that relies on standard names may not recognise them.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ALIASES_FILE = Path(__file__).parent.parent / "data" / "section_aliases.yaml"
MAX_HEADING_WORDS = 5


@lru_cache(maxsize=1)
def alias_map() -> dict[str, str]:
    raw = yaml.safe_load(ALIASES_FILE.read_text(encoding="utf-8"))
    return {alias.lower(): section for section, aliases in raw.items() for alias in aliases}


@dataclass
class SectionMap:
    found: dict[str, int] = field(default_factory=dict)   # canonical section -> line index of its heading
    nonstandard: list[str] = field(default_factory=list)  # heading-looking lines we didn't recognise


def normalize_heading(line: str) -> str:
    return line.strip().rstrip(":").strip().lower()


def find_sections(lines: list[str]) -> SectionMap:
    result = SectionMap()
    aliases = alias_map()
    for index, line in enumerate(lines):
        if len(line.split()) > MAX_HEADING_WORDS:
            continue
        section = aliases.get(normalize_heading(line))
        if section:
            result.found.setdefault(section, index)  # first occurrence wins
        elif _looks_like_heading(line):
            result.nonstandard.append(line.strip())
    return result


def _looks_like_heading(line: str) -> bool:
    text = line.strip().rstrip(":")
    return text.isupper() and len(text) >= 6 and all(ch.isalpha() or ch in " &" for ch in text)
