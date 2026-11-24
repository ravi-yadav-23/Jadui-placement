"""Build the question plan for a new interview.

Where questions come from, by track (n = question_count):

    fundamentals  n from the bank (chosen topics)                 0 LLM calls
    behavioral    n from the bank (HR/STAR)                        0 LLM calls
    resume        n about your projects/experience (LLM)           1 LLM call
    jd            n about the JD's requirements (LLM)              1 LLM call
    mixed         ~40% project (LLM) + 1 HR + rest fundamentals    0-1 LLM calls

LLM questions are grounded: each must cite ids that exist in the resume/JD input; questions
that cite nothing real are dropped and the plan is refilled from the fundamentals bank.
If fewer than half the requested LLM questions survive, planning fails instead of padding.
"""

from __future__ import annotations

import json

from app.core.db import Database
from app.core.errors import AppError
from app.interview.bank import BankQuestion, pick_questions
from app.interview.schemas import PlanDraft, PlannedQuestion
from app.resume.jd import get_jd
from app.resume.schemas import JobRequirements, ResumeProfile
from app.resume.service import get_resume

RECENT_SESSIONS = 3  # don't repeat bank questions seen in your last 3 interviews


def split_counts(track: str, count: int, has_resume: bool) -> dict[str, int]:
    """How many questions of each source a track gets."""
    if track == "mixed":
        project = max(1, round(count * 0.4)) if has_resume else 0
        return {"llm": project, "behavioral": 1, "fundamentals": count - project - 1}
    if track in ("resume", "jd"):
        return {"llm": count, "behavioral": 0, "fundamentals": 0}
    if track == "behavioral":
        return {"llm": 0, "behavioral": count, "fundamentals": 0}
    return {"llm": 0, "behavioral": 0, "fundamentals": count}


def recent_bank_ids(db: Database, user_id: str) -> set[str]:
    rows = db.list("interviews", user_id, columns="plan,created_at", limit=RECENT_SESSIONS)
    return {q.get("bank_id") for row in rows for q in (row.get("plan") or []) if q.get("bank_id")}


def build_plan(db: Database, llm, user_id: str, row: dict) -> list[PlannedQuestion]:
    settings = row["settings"]
    track, count = row["track"], settings["question_count"]
    profile = _profile(db, user_id, row.get("resume_id"))
    counts = split_counts(track, count, has_resume=profile is not None)
    exclude = recent_bank_ids(db, user_id)

    questions: list[PlannedQuestion] = []
    if counts["llm"]:
        if track == "jd":
            jd = JobRequirements.model_validate(get_jd(db, user_id, row["jd_id"])["parsed"])
            questions = plan_from_jd(llm, jd, profile, counts["llm"], row.get("target_role"))
        else:
            questions = plan_from_resume(llm, profile, counts["llm"], row.get("target_role"))
        if len(questions) * 2 < counts["llm"]:
            raise AppError("plan_failed", "Could not build enough questions from your resume. Try another track.")

    shortfall = counts["llm"] - len(questions)
    fundamentals = pick_questions(settings["topics"], settings["difficulty"], counts["fundamentals"] + shortfall,
                                  exclude, settings["seed"])
    behavioral = pick_questions(["behavioral"], "any", counts["behavioral"], exclude, settings["seed"])
    questions += [_from_bank(q) for q in fundamentals + behavioral]  # projects first, HR last (campus order)
    return [q.model_copy(update={"id": f"q{i}"}) for i, q in enumerate(questions)]


def _profile(db: Database, user_id: str, resume_id: str | None) -> ResumeProfile | None:
    if not resume_id:
        return None
    resume = get_resume(db, user_id, resume_id)
    return ResumeProfile.model_validate(resume["profile"]) if resume.get("profile") else None


def _from_bank(q: BankQuestion) -> PlannedQuestion:
    return PlannedQuestion(
        id="", type="behavioral" if q.topic == "behavioral" else "fundamentals",
        question=q.question, key_points=q.key_points, topic=q.topic, concept=q.concept, bank_id=q.id,
    )


def _entries(profile: ResumeProfile) -> list[dict]:
    """Projects first (students are asked about projects most), only bullets found in the resume text."""
    return [{
        "id": entry.id, "title": entry.title, "org": entry.org, "tech": entry.tech,
        "bullets": [{"id": b.id, "text": b.text} for b in entry.bullets if b.grounded],
    } for entry in profile.projects + profile.experience]


def plan_from_resume(llm, profile: ResumeProfile, count: int, target_role: str | None) -> list[PlannedQuestion]:
    items = _entries(profile)
    valid = {e["id"] for e in items} | {b["id"] for e in items for b in e["bullets"]}
    focus = "Ask about the candidate's projects and experience below."
    return _ask_llm(llm, "project", "projects", items, [], valid, count, target_role, focus)


def plan_from_jd(llm, jd: JobRequirements, profile: ResumeProfile | None, count: int,
                 target_role: str | None) -> list[PlannedQuestion]:
    # Must-have requirements first; nice-to-haves only if there are not enough must-haves.
    ordered = sorted(jd.requirements, key=lambda r: r.kind != "must")
    items = [{"id": r.id, "requirement": r.text, "kind": r.kind, "skills": r.skills} for r in ordered]
    context = _entries(profile) if profile else []
    focus = (f"Each question tests one job requirement below for the role '{jd.title}'. Where the "
             "candidate's experience is relevant, ask how they applied it; otherwise ask how they would.")
    return _ask_llm(llm, "jd", None, items, context, {r.id for r in jd.requirements}, count,
                    target_role or jd.title, focus)


def _ask_llm(llm, question_type, topic, items, context, valid_ids, count, target_role, focus):
    if not items:
        return []
    draft = llm.structured("interview_plan", PlanDraft, {
        "count": str(count), "focus": focus, "target_role": target_role or "Software Engineer",
        "items_json": json.dumps(items, indent=1), "context_json": json.dumps(context, indent=1),
    }, temperature=0.4)

    questions = []
    for q in draft.questions[:count]:
        cited = [i for i in q.source_ids if i in valid_ids]
        if not cited or not q.question.strip() or len(q.key_points) < 2:
            continue  # not grounded in the input: drop it
        questions.append(PlannedQuestion(
            id="", type=question_type, question=q.question.strip(), key_points=q.key_points[:5],
            topic=topic or q.concept, concept=q.concept, source_ids=cited,
        ))
    return questions
