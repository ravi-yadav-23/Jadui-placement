"""The interview state machine, as pure functions (no database, no LLM): easy to test every branch.

After each answer is judged, `next_step()` decides what the interviewer does next:

    main answer judged, follow-up proposed  -> ask the follow-up (max 1 per question)
    otherwise, more questions in the plan   -> ask the next planned question
    otherwise                               -> finish the interview

Skipping a question never triggers a follow-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.interview.schemas import PlannedQuestion


@dataclass(frozen=True)
class Step:
    action: Literal["follow_up", "ask", "finish"]
    question_id: str | None = None
    text: str | None = None


def next_question(plan: list[PlannedQuestion], question_id: str) -> PlannedQuestion | None:
    """The planned question after `question_id`, or None if it was the last one."""
    ids = [q.id for q in plan]
    position = ids.index(question_id) + 1
    return plan[position] if position < len(plan) else None


def next_step(plan: list[PlannedQuestion], turn_kind: str, question_id: str,
              follow_up: str | None, skipped: bool = False) -> Step:
    if turn_kind == "main" and follow_up and not skipped:
        return Step("follow_up", question_id, follow_up)
    upcoming = next_question(plan, question_id)
    if upcoming:
        return Step("ask", upcoming.id, upcoming.question)
    return Step("finish")


def question_number(plan: list[PlannedQuestion], question_id: str) -> int:
    """1-based position of a question in the plan ('Question 2 of 5')."""
    return [q.id for q in plan].index(question_id) + 1
