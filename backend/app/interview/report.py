"""Build the end-of-interview report from the plan and the judged turns. No LLM call.

Per question: coverage counts key points covered in the main answer OR its follow-up;
rubric = mean of both turns' rubric scores (see scoring.py). Skipped = 0. A question whose
evaluation failed, or that was never answered (ended early), is left out.

Skill gaps (written to skill_gaps, read by the planner):
  * fundamentals question scoring < 60 -> "OS: Deadlocks"           (severity general)
  * JD question scoring < 60            -> the requirement's skill   (severity must_have)
  * any dimension averaging <= 2 of 5   -> e.g. "Explaining trade-offs" (severity general)
"""

from __future__ import annotations

from collections import defaultdict

from app.interview.delivery import delivery_metrics
from app.interview.rubric import gap_label, label
from app.interview.schemas import (
    CoveredPoint,
    DeliverySummary,
    InterviewReport,
    PlannedQuestion,
    QuestionReport,
    TurnEvaluation,
)
from app.interview.scoring import band, combine, coverage_score, session_score

GAP_SCORE = 60
GAP_ANCHOR = 2.0
TOPIC_NAMES = {"os": "OS", "dbms": "DBMS", "cn": "Computer Networks", "oop": "OOP"}


def build_report(plan: list[PlannedQuestion], turns: list[dict]) -> tuple[InterviewReport, list[tuple[str, str]]]:
    """Returns (report, gaps) where gaps = [(skill, severity), ...]."""
    questions: list[QuestionReport] = []
    anchors: dict[str, list[int]] = defaultdict(list)
    gaps: list[tuple[str, str]] = []

    for planned in plan:
        q_turns = [t for t in turns if t["question_id"] == planned.id]
        if not q_turns:
            continue  # never asked (interview ended early)
        if q_turns[0]["status"] == "skipped":
            questions.append(QuestionReport(question_id=planned.id, type=planned.type, topic=planned.topic,
                                            question=planned.question, score=0, skipped=True,
                                            missed=planned.key_points))
        else:
            evaluations = [TurnEvaluation.model_validate(t["evaluation"]) for t in q_turns
                           if t["status"] == "evaluated"]
            if not evaluations:
                continue  # unanswered or evaluation failed
            questions.append(_question_report(planned, evaluations))
            for evaluation in evaluations:
                for dim in evaluation.dimensions:
                    anchors[dim.name].append(dim.anchor)

        latest = questions[-1]
        if latest.score < GAP_SCORE and planned.type == "fundamentals":
            gaps.append((f"{TOPIC_NAMES.get(planned.topic, planned.topic)}: {planned.concept}", "general"))
        elif latest.score < GAP_SCORE and planned.type == "jd":
            gaps.append((planned.concept or planned.topic, "must_have"))

    dimension_means = {name: sum(v) / len(v) for name, v in anchors.items()}
    gaps += [(gap_label(name), "general") for name, mean in dimension_means.items() if mean <= GAP_ANCHOR]

    score = session_score([q.score for q in questions])
    report = InterviewReport(
        score=score,
        band=band(score),
        dimensions={label(name): round(mean, 1) for name, mean in dimension_means.items()},
        topics=_topic_averages(questions),
        questions=questions,
        delivery=_delivery_summary(turns),
        gaps=list(dict.fromkeys(skill for skill, _ in gaps)),
    )
    return report, list(dict.fromkeys(gaps))


def _question_report(planned: PlannedQuestion, evaluations: list[TurnEvaluation]) -> QuestionReport:
    covered: dict[str, CoveredPoint] = {}
    for evaluation in evaluations:
        for point in evaluation.covered:
            covered.setdefault(point.point, point)
    rubric = sum(e.rubric for e in evaluations) / len(evaluations)
    coverage = coverage_score(len(covered), len(planned.key_points))
    return QuestionReport(
        question_id=planned.id, type=planned.type, topic=planned.topic, question=planned.question,
        score=combine(rubric, coverage),
        covered=[covered[p] for p in planned.key_points if p in covered],
        missed=[p for p in planned.key_points if p not in covered],
    )


def _topic_averages(questions: list[QuestionReport]) -> dict[str, int]:
    scores: dict[str, list[int]] = defaultdict(list)
    for q in questions:
        scores[q.topic].append(q.score)
    return {topic: round(sum(v) / len(v)) for topic, v in scores.items()}


def _delivery_summary(turns: list[dict]) -> DeliverySummary | None:
    voice = [t for t in turns if t.get("answer_mode") == "voice" and t.get("answer")]
    if not voice:
        return None
    words = sum(t["delivery"]["words"] for t in voice)
    fillers = sum(t["delivery"]["fillers"] for t in voice)
    timed = [t for t in voice if t["delivery"].get("wpm")]
    minutes = sum(t["duration_seconds"] for t in timed) / 60
    timed_words = sum(t["delivery"]["words"] for t in timed)
    return DeliverySummary(
        voice_answers=len(voice),
        wpm=round(timed_words / minutes) if minutes else None,
        fillers_per_100_words=round(fillers / words * 100, 1) if words else 0.0,
        repeated=delivery_metrics(" ".join(t["answer"] for t in voice)).repeated,
    )
