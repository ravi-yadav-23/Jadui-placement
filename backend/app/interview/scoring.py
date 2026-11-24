"""Interview scoring formulas. Pure functions; the UI shows these same formulas.

  rubric   = mean over dimensions of (anchor - 1) / 4 * 100        anchor 1 -> 0, anchor 5 -> 100
  coverage = verified covered key points / all key points * 100
  turn     = round(0.6 * rubric + 0.4 * coverage)

A QUESTION combines its main answer and its follow-up: coverage counts key points covered in
either answer, rubric is the mean of both turns. A skipped question scores 0.
SESSION = mean of question scores. Band: Ready >= 75, Almost there 55-74, Needs practice < 55.
"""

from __future__ import annotations

from app.interview.schemas import DimensionScore

RUBRIC_WEIGHT = 0.6
COVERAGE_WEIGHT = 0.4


def anchor_to_100(anchor: float) -> float:
    return (anchor - 1) / 4 * 100


def rubric_score(dimensions: list[DimensionScore]) -> int:
    if not dimensions:
        return 0
    return round(sum(anchor_to_100(d.anchor) for d in dimensions) / len(dimensions))


def coverage_score(covered: int, total: int) -> int:
    return round(covered / total * 100) if total else 0


def combine(rubric: float, coverage: float) -> int:
    return round(RUBRIC_WEIGHT * rubric + COVERAGE_WEIGHT * coverage)


def session_score(question_scores: list[int]) -> int:
    return round(sum(question_scores) / len(question_scores)) if question_scores else 0


def band(score: int) -> str:
    if score >= 75:
        return "ready"
    if score >= 55:
        return "almost"
    return "practice"
