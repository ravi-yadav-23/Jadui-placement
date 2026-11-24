"""Judge one answer: one LLM call, then code checks the model's claims before anything is scored.

    evaluation = judge_answer(llm, planned, "main", planned.question, answer, target_role)

Checks done by code (not trusted to the model):
  * a key point counts as covered ONLY if its quote really appears in the answer (fuzzy match >= 90,
    the same grounding check the resume screener uses for bullets). Failed quotes are "demoted".
  * only the dimensions defined for this question type are kept (rubrics.yaml).
  * a follow-up is kept only for a main answer that missed at least one key point.
"""

from __future__ import annotations

import json

from app.interview.rubric import anchors_text, dimensions_for
from app.interview.schemas import CoveredPoint, JudgeDraft, PlannedQuestion, TurnEvaluation
from app.interview.scoring import combine, coverage_score, rubric_score
from app.resume.pipeline.structure import is_grounded, normalize


def judge_answer(llm, question: PlannedQuestion, kind: str, asked: str, answer: str, target_role: str | None,
                 previous: tuple[str, str] | None = None) -> TurnEvaluation:
    """`asked` = the text actually asked (the follow-up text for a follow-up turn).
    `previous` = (question, answer) of the main turn, when judging its follow-up."""
    previous_text = ""
    if previous:
        previous_text = (f"\nEarlier in this question the candidate was asked:\n{previous[0]}\n"
                         f"and answered:\n{previous[1]}\n")
    draft = llm.structured("interview_judge", JudgeDraft, {
        "target_role": target_role or "Software Engineer",
        "question_type": question.type,
        "turn_kind": kind,
        "previous_turn": previous_text,
        "question": asked,
        "key_points_json": json.dumps(question.key_points, indent=1),
        "dimension_names": ", ".join(dimensions_for(question.type)),
        "anchors": anchors_text(question.type),
        "answer": answer,
    })
    return verify_and_score(question, kind, answer, draft)


def verify_and_score(question: PlannedQuestion, kind: str, answer: str, draft: JudgeDraft) -> TurnEvaluation:
    """Pure function: turn the model's raw judgment into a verified, scored evaluation."""
    source = normalize(answer)
    covered_by_index: dict[int, CoveredPoint] = {}
    demoted = 0
    for judgment in draft.key_points:
        in_range = 0 <= judgment.index < len(question.key_points)
        if not (judgment.covered and in_range) or judgment.index in covered_by_index:
            continue
        if judgment.quote and is_grounded(judgment.quote, source):
            covered_by_index[judgment.index] = CoveredPoint(point=question.key_points[judgment.index],
                                                            quote=judgment.quote.strip())
        else:
            demoted += 1

    covered = [covered_by_index[i] for i in sorted(covered_by_index)]
    missed = [p for i, p in enumerate(question.key_points) if i not in covered_by_index]

    expected = dimensions_for(question.type)
    dimensions = []
    for name in expected:  # keep one score per expected dimension, in rubric order
        match = next((d for d in draft.dimensions if d.name == name), None)
        if match:
            dimensions.append(match)

    coverage = coverage_score(len(covered), len(question.key_points))
    rubric = rubric_score(dimensions) if dimensions else coverage  # model skipped all dimensions: coverage only
    follow_up = (draft.follow_up or "").strip() or None
    return TurnEvaluation(
        covered=covered,
        missed=missed,
        dimensions=dimensions,
        rubric=rubric,
        coverage=coverage,
        score=combine(rubric, coverage),
        feedback=draft.feedback.strip(),
        follow_up=follow_up if kind == "main" and missed else None,
        demoted_quotes=demoted,
    )
