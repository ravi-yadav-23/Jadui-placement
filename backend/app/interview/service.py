"""Orchestration for mock interviews: the API calls these; they call the engine, judge and database.

Flow:
  POST /interviews             -> row (planning). Bank-only tracks are planned right away;
                                  resume/JD tracks plan in the background (1 LLM call) -> active
  POST .../turns/{id}/answer   -> store answer (evaluating) -> 202; background: evaluate_turn()
  evaluate_turn()              -> judge -> engine.next_step(): follow-up | next question | finish
  frontend                     -> polls GET /interviews/{id}

Every background function catches its own errors and writes them to the row, like resume v2.
"""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.db import Database, utc_now
from app.core.errors import AppError
from app.interview.delivery import delivery_metrics
from app.interview.engine import next_step, question_number
from app.interview.evaluate import judge_answer
from app.interview.planner import build_plan, split_counts
from app.interview.report import build_report
from app.interview.schemas import AnswerRequest, CreateInterview, PlannedQuestion, TurnOut
from app.llm.client import PROMPT_VERSIONS, get_llm
from app.resume.jd import get_jd
from app.resume.service import enforce_daily_limit, get_resume, is_stale

log = logging.getLogger(__name__)

TURN_STALE_AFTER = timedelta(minutes=2)  # an answer still "evaluating" after this was lost (server restart)


# ---------- Create + plan ----------

def create_interview(db: Database, user_id: str, request: CreateInterview) -> tuple[dict, bool]:
    """Returns (row, needs_background_planning)."""
    if request.track == "resume" and not request.resume_id:
        raise AppError("resume_required", "Choose a resume for a resume deep-dive.", 422)
    if request.track == "jd" and not request.jd_id:
        raise AppError("jd_required", "Choose a job description for a JD interview.", 422)
    if request.resume_id and get_resume(db, user_id, request.resume_id)["status"] != "ready":
        raise AppError("not_ready", "The resume is still being processed.", 409)
    if request.jd_id and get_jd(db, user_id, request.jd_id)["status"] != "ready":
        raise AppError("not_ready", "The job description is still being parsed.", 409)
    enforce_daily_limit(db, user_id, "interviews", settings.DAILY_INTERVIEW_LIMIT)

    row = db.insert("interviews", user_id, {
        "track": request.track,
        "mode": request.mode,
        "resume_id": request.resume_id,
        "jd_id": request.jd_id if request.track == "jd" else None,
        "target_role": request.target_role,
        "settings": {"question_count": request.question_count, "topics": request.topics,
                     "difficulty": request.difficulty, "seed": random.randint(1, 10**9)},
        "status": "planning",
        "plan": [],
        "prompt_versions": {n: PROMPT_VERSIONS[n] for n in ("interview_plan", "interview_judge")},
    })
    uses_llm = split_counts(request.track, request.question_count, bool(request.resume_id))["llm"] > 0
    if not uses_llm:
        plan_interview(db, user_id, row["id"])  # bank only: fast, no LLM
        return db.get("interviews", user_id, row["id"]), False
    return row, True


def plan_interview(db: Database, user_id: str, interview_id: str) -> None:
    """Build the plan and ask the first question. Never raises."""
    row = db.get("interviews", user_id, interview_id)
    try:
        plan = build_plan(db, get_llm(db, user_id), user_id, row)
        db.update("interviews", user_id, interview_id, {"plan": [q.model_dump() for q in plan], "status": "active"})
        _ask(db, user_id, interview_id, idx=0, question_id=plan[0].id, kind="main", text=plan[0].question)
    except AppError as exc:
        db.update("interviews", user_id, interview_id, {"status": "failed", "error": exc.message})
    except Exception:
        log.exception("planning interview %s failed", interview_id)
        db.update("interviews", user_id, interview_id, {"status": "failed", "error": "Could not plan the interview."})


def _ask(db: Database, user_id: str, interview_id: str, idx: int, question_id: str, kind: str, text: str) -> None:
    db.insert("interview_turns", user_id, {
        "interview_id": interview_id, "idx": idx, "question_id": question_id,
        "kind": kind, "question": text, "status": "asked",
    })


# ---------- Read ----------

def load(db: Database, user_id: str, interview_id: str) -> tuple[dict, list[dict]]:
    row = db.get("interviews", user_id, interview_id)
    if row is None:
        raise AppError("not_found", "Interview not found", 404)
    if row["status"] == "planning" and is_stale(row["created_at"]):
        row = db.update("interviews", user_id, interview_id, {
            "status": "failed", "error": "Planning was interrupted. Please start a new interview."})
    turns = sorted(db.list("interview_turns", user_id, limit=100, interview_id=interview_id), key=lambda t: t["idx"])
    for turn in turns:
        if turn["status"] == "evaluating" and _older_than(turn.get("answered_at"), TURN_STALE_AFTER):
            turn.update(db.update("interview_turns", user_id, turn["id"], {
                "status": "failed", "error": "Evaluation was interrupted. Retry it."}))
    return row, turns


def _older_than(iso: str | None, age: timedelta) -> bool:
    return bool(iso) and datetime.now(UTC) - datetime.fromisoformat(iso) > age


def plan_of(row: dict) -> list[PlannedQuestion]:
    return [PlannedQuestion.model_validate(q) for q in row.get("plan") or []]


def view(row: dict, turns: list[dict]) -> dict:
    """What the browser may see. Never the plan (upcoming questions + answer key).
    In interview mode, scores and feedback stay hidden until the interview is completed."""
    plan = plan_of(row)
    show_feedback = row["mode"] == "practice" or row["status"] == "completed"
    out_turns = []
    for t in turns:
        turn = TurnOut.model_validate(t).model_dump()
        if not show_feedback:
            turn.update(score=None, evaluation=None)
        out_turns.append(turn)
    number = question_number(plan, turns[-1]["question_id"]) if plan and turns else 0
    public = {k: v for k, v in row.items() if k not in ("plan", "settings")}  # the plan holds the answer key
    return {**public, "question_count": len(plan) or row["settings"]["question_count"],
            "question_number": number, "turns": out_turns}


# ---------- Answer + judge ----------

def _current(row: dict, turns: list[dict]) -> dict:
    if row["status"] != "active" or not turns:
        raise AppError("not_active", "This interview is not in progress.", 409)
    return turns[-1]


def submit_answer(db: Database, user_id: str, interview_id: str, turn_id: str, request: AnswerRequest) -> None:
    row, turns = load(db, user_id, interview_id)
    turn = _current(row, turns)
    if turn["id"] != turn_id:
        raise AppError("turn_not_current", "That question is no longer the current one.", 409)
    if turn["status"] != "asked":
        raise AppError("already_answered", "This question was already answered.", 409)
    answer = request.answer.strip()
    if not answer:
        raise AppError("empty_answer", "Write or say an answer first (or skip the question).", 422)
    if len(answer) > settings.INTERVIEW_MAX_ANSWER_CHARS:
        raise AppError("answer_too_long", f"Answers are limited to {settings.INTERVIEW_MAX_ANSWER_CHARS} characters.",
                       422)
    duration = request.duration_seconds if request.answer_mode == "voice" else None
    db.update("interview_turns", user_id, turn_id, {
        "answer": answer, "answer_mode": request.answer_mode, "duration_seconds": request.duration_seconds,
        "delivery": delivery_metrics(answer, duration).model_dump(),
        "status": "evaluating", "error": None, "answered_at": utc_now(),
    })


def retry_turn(db: Database, user_id: str, interview_id: str, turn_id: str) -> None:
    row, turns = load(db, user_id, interview_id)
    turn = _current(row, turns)
    if turn["id"] != turn_id or turn["status"] != "failed":
        raise AppError("not_failed", "Only a failed evaluation can be retried.", 409)
    db.update("interview_turns", user_id, turn_id, {"status": "evaluating", "error": None, "answered_at": utc_now()})


def evaluate_turn(db: Database, user_id: str, interview_id: str, turn_id: str) -> None:
    """Background job: judge the answer, then let the engine pick the next step. Never raises."""
    try:
        row, turns = load(db, user_id, interview_id)
        turn = next(t for t in turns if t["id"] == turn_id)
        plan = plan_of(row)
        planned = next(q for q in plan if q.id == turn["question_id"])
        previous = None
        if turn["kind"] == "follow_up":
            main = next(t for t in turns if t["question_id"] == planned.id and t["kind"] == "main")
            previous = (main["question"], main["answer"] or "")
        evaluation = judge_answer(get_llm(db, user_id), planned, turn["kind"], turn["question"], turn["answer"],
                                  row.get("target_role"), previous)
        db.update("interview_turns", user_id, turn_id, {
            "evaluation": evaluation.model_dump(), "score": evaluation.score, "status": "evaluated"})
        _advance(db, user_id, row, plan, turn, evaluation.follow_up)
    except AppError as exc:
        db.update("interview_turns", user_id, turn_id, {"status": "failed", "error": exc.message})
    except Exception:
        log.exception("evaluating turn %s failed", turn_id)
        db.update("interview_turns", user_id, turn_id, {"status": "failed", "error": "Could not evaluate the answer."})


def _advance(db: Database, user_id: str, row: dict, plan: list[PlannedQuestion], turn: dict,
             follow_up: str | None, skipped: bool = False) -> None:
    step = next_step(plan, turn["kind"], turn["question_id"], follow_up, skipped)
    if step.action == "finish":
        complete(db, user_id, row["id"])
        return
    kind = "follow_up" if step.action == "follow_up" else "main"
    _ask(db, user_id, row["id"], idx=turn["idx"] + 1, question_id=step.question_id, kind=kind, text=step.text)


# ---------- Skip / finish / delete ----------

def skip(db: Database, user_id: str, interview_id: str) -> None:
    row, turns = load(db, user_id, interview_id)
    turn = _current(row, turns)
    if turn["status"] != "asked":
        raise AppError("cannot_skip", "Only an unanswered question can be skipped.", 409)
    db.update("interview_turns", user_id, turn["id"], {"status": "skipped", "answered_at": utc_now()})
    _advance(db, user_id, row, plan_of(row), turn, follow_up=None, skipped=True)


def finish(db: Database, user_id: str, interview_id: str) -> None:
    """End early: the open (unanswered) question is dropped; the report covers what was answered."""
    row, turns = load(db, user_id, interview_id)
    turn = _current(row, turns)
    if turn["status"] == "evaluating":
        raise AppError("still_evaluating", "Wait a moment: your last answer is still being evaluated.", 409)
    if turn["status"] in ("asked", "failed"):
        db.delete("interview_turns", user_id, turn["id"])
    complete(db, user_id, interview_id)


def complete(db: Database, user_id: str, interview_id: str) -> None:
    row, turns = load(db, user_id, interview_id)
    report, gaps = build_report(plan_of(row), turns)
    db.update("interviews", user_id, interview_id, {
        "status": "completed", "score": report.score, "report": report.model_dump(), "completed_at": utc_now()})
    db.upsert_many("skill_gaps", [
        {"user_id": user_id, "skill": skill, "severity": severity, "source": "interview", "source_id": interview_id}
        for skill, severity in gaps
    ], on_conflict="user_id,skill,source,source_id")


def delete_interview(db: Database, user_id: str, interview_id: str) -> None:
    _, turns = load(db, user_id, interview_id)
    for turn in turns:
        db.delete("interview_turns", user_id, turn["id"])
    for gap in db.list("skill_gaps", user_id, limit=100, source="interview", source_id=interview_id):
        db.delete("skill_gaps", user_id, gap["id"])
    db.delete("interviews", user_id, interview_id)
