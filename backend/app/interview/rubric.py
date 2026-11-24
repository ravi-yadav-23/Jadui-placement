"""Anchored rating scales from data/rubrics.yaml.

`dimensions_for("fundamentals")` -> ["correctness", "depth", "clarity"]
`anchors_text("fundamentals")`   -> the scale written out for the judge prompt (and shown in the UI)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

RUBRIC_FILE = Path(__file__).parent / "data" / "rubrics.yaml"


@lru_cache(maxsize=1)
def load_rubric() -> dict[str, dict]:
    dimensions = yaml.safe_load(RUBRIC_FILE.read_text(encoding="utf-8"))["dimensions"]
    for name, spec in dimensions.items():
        if sorted(spec["anchors"]) != [1, 2, 3, 4, 5]:
            raise ValueError(f"Dimension '{name}' must have anchors 1-5")
    return dimensions


def dimensions_for(question_type: str) -> list[str]:
    return [name for name, spec in load_rubric().items() if question_type in spec["types"]]


def anchors_text(question_type: str) -> str:
    lines = []
    for name in dimensions_for(question_type):
        spec = load_rubric()[name]
        lines.append(f'"{name}" ({spec["label"]}):')
        lines += [f"  {level} = {text}" for level, text in sorted(spec["anchors"].items())]
    return "\n".join(lines)


def gap_label(dimension: str) -> str:
    return load_rubric()[dimension]["gap"]


def label(dimension: str) -> str:
    return load_rubric()[dimension]["label"]
