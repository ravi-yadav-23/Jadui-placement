"""Orchestration for the planner: profile, plans, tasks, re-planning, check-ins (plan §6).

The core idea is ONE re-plan function, `refresh()`:
  mark tasks from earlier days that were never done as missed (kept as history, so check-ins can count them),
  delete every unfinished task from today on, re-run the scheduler from today with the real progress
  (missed work is still "remaining" on its topic, so it comes back), and store the next 14 days of tasks.
It runs when you open the planner and tasks were missed, when fewer than 7 days of tasks are left, once a week,
after a check-in, and on "Re-plan". Pinned (moved) tasks are kept and their time is reserved.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta

from app.core.config import settings
from app.core.db import Database, utc_now
from app.core.errors import AppError
from app.llm.client import get_llm
from app.planner import text
from app.planner.builder import DEFAULT_FACTOR, BuiltPlan, allocation, build_plan, schedule_topics
from app.planner.capacity import day_minutes
from app.planner.curriculum import CURRICULUM_VERSION, load_curriculum
from app.planner.schemas import (
    CheckinRequest,
    PlannerProfile,
    PlanTopic,
    ProfileResponse,
    ProfileSuggestions,
    TaskUpdate,
)
from app.planner.selection import CS_SUBJECTS, minutes_per_problem

log = logging.getLogger(__name__)

CS_GAP_LABELS = {"os": "OS", "dbms": "DBMS", "cn": "Computer Networks", "oop": "OOP"}  # interview gap prefixes
RELEARN_MINUTES = 90
MIN_FACTOR, MAX_FACTOR = 0.4, DEFAULT_FACTOR


def today() -> date:
    """One place for "today" so tests can move time."""
    return date.today()


# ---------- Profile ----------

def get_profile(db: Database, user_id: str) -> ProfileResponse:
    row = db.find_one("planner_profiles", user_id)
    return ProfileResponse(profile=PlannerProfile.model_validate(row["answers"]) if row else None,
                           suggestions=suggestions(db, user_id))


def save_profile(db: Database, user_id: str, profile: PlannerProfile) -> PlannerProfile:
    answers = profile.model_dump(mode="json")
    row = db.find_one("planner_profiles", user_id)
    if row:
        db.update("planner_profiles", user_id, row["id"], {"answers": answers, "updated_at": utc_now()})
    else:
        db.insert("planner_profiles", user_id, {"answers": answers})
    return profile


def suggestions(db: Database, user_id: str) -> ProfileSuggestions:
    """What the other pillars already know, offered as pre-filled answers."""
    out = ProfileSuggestions()
    resume = next((r for r in db.list("resumes", user_id, columns="id,title,status,profile,created_at", limit=10)
                   if r["status"] == "ready" and r.get("profile")), None)
    if resume:
        profile = resume["profile"]
        out.resume_title = resume["title"]
        out.projects = min(len(profile.get("projects") or []), 3)
        out.stack = (profile.get("skills") or [])[:12]
    out.gaps = list(dict.fromkeys(g["skill"] for g in open_gaps(db, user_id)))[:12]
    out.interview_topics = interview_topic_scores(db, user_id)
    out.ratings = {t: (3 if s >= 75 else 2 if s >= 60 else 1) for t, s in out.interview_topics.items()}
    return out


def open_gaps(db: Database, user_id: str) -> list[dict]:
    return [g for g in db.list("skill_gaps", user_id, columns="id,skill,source,source_id,resolved_at,created_at",
                               limit=300) if not g.get("resolved_at")]


def interview_topic_scores(db: Database, user_id: str, after: str | None = None) -> dict[str, int]:
    """Average score per CS topic over completed mock interviews (optionally only those after a time)."""
    scores: dict[str, list[int]] = defaultdict(list)
    for row in db.list("interviews", user_id, columns="status,report,completed_at,created_at", limit=30):
        too_old = after and (row.get("completed_at") or "") <= after
        if row["status"] != "completed" or not row.get("report") or too_old:
            continue
        for topic, score in row["report"]["topics"].items():
            if topic in CS_SUBJECTS:
                scores[topic].append(score)
    return {t: round(sum(v) / len(v)) for t, v in scores.items()}


def _gap_inputs(db: Database, user_id: str, include: list[str]) -> list[tuple[str, str]]:
    wanted = set(include)
    seen: dict[str, str] = {}
    for gap in open_gaps(db, user_id):
        if gap["skill"] in wanted and gap["skill"] not in seen:
            seen[gap["skill"]] = "interview" if gap["source"] == "interview" else gap["source"]
    return list(seen.items())


# ---------- Create ----------

def _check_dates(profile: PlannerProfile) -> None:
    if profile.target_date and not today() + timedelta(days=7) <= profile.target_date <= today() + timedelta(days=730):
        raise AppError("bad_target_date", "Choose a target date between one week and two years from today.", 422)


def preview(db: Database, user_id: str, profile: PlannerProfile) -> BuiltPlan:
    _check_dates(profile)
    return build_plan(profile, today(), _gap_inputs(db, user_id, profile.include_gaps),
                      interview_topic_scores(db, user_id))


def create_plan(db: Database, user_id: str, profile: PlannerProfile) -> dict:
    built = preview(db, user_id, profile)
    save_profile(db, user_id, profile)
    for old in db.list("plans", user_id, columns="id,status,created_at", limit=20):
        if old["status"] == "active":
            db.update("plans", user_id, old["id"], {"status": "archived"})

    labels = {s: sub.label for s, sub in load_curriculum().items()}
    facts = text.summary_facts(profile, list(built.weights), labels,
                               [{"name": p.name} for p in built.schedule.roadmap.phases], built.feasibility.cut)
    plan = db.insert("plans", user_id, {
        "status": "active",
        "start_date": built.start.isoformat(),
        "target_date": built.target.isoformat(),
        "profile_snapshot": profile.model_dump(mode="json"),
        "settings": {"weights": built.weights, "minutes_per_problem": minutes_per_problem(profile)},
        "allocation": [a.model_dump() for a in built.allocation],
        "roadmap": built.schedule.roadmap.model_dump(mode="json"),
        "feasibility": built.feasibility.model_dump(),
        "capacity_factor": DEFAULT_FACTOR,
        "summary": text.template_summary(facts).model_dump(),
        "curriculum_version": CURRICULUM_VERSION,
        "refreshed_on": today().isoformat(),
    })
    db.insert_many("plan_topics", user_id, [{**t.model_dump(mode="json"), "plan_id": plan["id"]} for t in built.topics])
    _store_horizon(db, user_id, plan["id"], built, kept_per_day={})
    return plan


def write_plan_text(db: Database, user_id: str, plan_id: str) -> None:
    """Background job: AI roadmap explanation + project ideas. Keeps the template text if anything fails."""
    plan = db.get("plans", user_id, plan_id)
    profile = PlannerProfile.model_validate(plan["profile_snapshot"])
    labels = {s: sub.label for s, sub in load_curriculum().items()}
    weights = plan["settings"]["weights"]
    facts = text.summary_facts(profile, list(weights), labels,
                               [{"name": p["name"]} for p in plan["roadmap"]["phases"]], plan["feasibility"]["cut"])
    try:
        llm = get_llm(db, user_id)
        update = {"summary": text.ai_summary(llm, facts, set(weights)).model_dump()}
    except Exception as exc:  # noqa: BLE001 - template stays; the plan works without the LLM
        log.warning("planner summary fell back to template: %s", exc)
        update, llm = {}, None
    if "projects" in weights and llm is not None:
        try:
            resume = next((r for r in db.list("resumes", user_id, columns="status,profile,created_at", limit=10)
                           if r["status"] == "ready" and r.get("profile")), None)
            resume_projects = [p["title"] for p in (resume or {}).get("profile", {}).get("projects", [])]
            resume_skills = (resume or {}).get("profile", {}).get("skills", [])[:15]
            candidate = text.project_inputs(profile, resume_projects, resume_skills, profile.include_gaps[:6])
            update["projects"] = [p.model_dump() for p in text.ai_projects(llm, candidate)]
        except Exception as exc:  # noqa: BLE001
            log.warning("planner project ideas failed: %s", exc)
    if update:
        db.update("plans", user_id, plan_id, update)


# ---------- Read ----------

def current_plan(db: Database, user_id: str) -> dict:
    plan = db.find_one("plans", user_id, status="active")
    if plan is None:
        raise AppError("no_plan", "You don't have a plan yet. Answer a few questions to create one.", 404)
    return plan


def load_topics(db: Database, user_id: str, plan_id: str) -> list[PlanTopic]:
    rows = db.list("plan_topics", user_id, limit=500, plan_id=plan_id)
    return [PlanTopic.model_validate(r) for r in sorted(rows, key=lambda r: (r["subject"], r["position"]))]


def plan_tasks(db: Database, user_id: str, plan_id: str, start: date | None = None,
               end: date | None = None) -> list[dict]:
    rows = db.list("plan_tasks", user_id, limit=3000, plan_id=plan_id)
    rows = [r for r in rows if (start is None or _d(r["date"]) >= start) and (end is None or _d(r["date"]) <= end)]
    return sorted(rows, key=lambda r: (str(r["date"]), r["position"]))


def _d(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def plan_view(db: Database, user_id: str, plan: dict) -> dict:
    """Plan row + live progress, in the PlanDetail shape."""
    topics = load_topics(db, user_id, plan["id"])
    weights = plan["settings"]["weights"]
    start, target = _d(plan["start_date"]), _d(plan["target_date"])
    profile = PlannerProfile.model_validate(plan["profile_snapshot"])
    days = max((target - start).days + 1, 1)
    usable = sum(int(day_minutes(profile, start + timedelta(i)) * plan["capacity_factor"]) for i in range(days))
    return {
        **plan,
        "capacity_factor": float(plan["capacity_factor"]),
        "weeks": round(days / 7, 1),
        "hours_per_week": round(usable / 60 / (days / 7), 1),
        "allocation": [a.model_dump() for a in allocation(topics, weights)],
        "topics": [t.model_dump() for t in topics],
        "study_time": profile.study_time,
    }


# ---------- Re-plan ----------

def needs_refresh(db: Database, user_id: str, plan: dict) -> bool:
    now = today()
    if now > _d(plan["target_date"]):
        return False
    tasks = plan_tasks(db, user_id, plan["id"])
    missed = any(t["status"] == "todo" and _d(t["date"]) < now for t in tasks)
    last = max((_d(t["date"]) for t in tasks), default=now - timedelta(days=1))
    stale = not plan.get("refreshed_on") or _d(plan["refreshed_on"]) <= now - timedelta(days=7)
    return missed or last < now + timedelta(days=7) or stale


def refresh(db: Database, user_id: str, plan: dict) -> dict:
    now = today()
    if now > _d(plan["target_date"]):
        return plan
    _ingest_interviews(db, user_id, plan)
    tasks = plan_tasks(db, user_id, plan["id"])
    for missed in (t for t in tasks if t["status"] == "todo" and _d(t["date"]) < now):
        db.update("plan_tasks", user_id, missed["id"], {"status": "skipped", "details": {**missed["details"],
                                                                                          "missed": True}})
    pinned = [t for t in tasks if t["status"] == "todo" and _d(t["date"]) >= now and t["details"].get("pinned")]
    stale = [t for t in tasks if t["status"] == "todo" and _d(t["date"]) >= now and t not in pinned]
    db.delete_many("plan_tasks", user_id, [t["id"] for t in stale])

    reserved: dict[date, int] = defaultdict(int)
    pinned_minutes: dict[str, int] = defaultdict(int)
    for t in pinned:
        reserved[_d(t["date"])] += t["minutes"]
        if t["topic_id"] and t["kind"] != "review":
            pinned_minutes[t["topic_id"]] += t["minutes"]
    topics = load_topics(db, user_id, plan["id"])
    for_scheduling = [t.model_copy(update={"done_minutes": t.done_minutes + pinned_minutes[t.topic_id]})
                      for t in topics]

    profile = PlannerProfile.model_validate(plan["profile_snapshot"])
    built = schedule_topics(profile, for_scheduling, plan["settings"]["weights"], now, _d(plan["target_date"]),
                            float(plan["capacity_factor"]), plan["settings"]["minutes_per_problem"], dict(reserved))
    status_by_id = {t.topic_id: t.status for t in built.topics}
    for topic_row in db.list("plan_topics", user_id, limit=500, plan_id=plan["id"]):
        new = status_by_id.get(topic_row["topic_id"])
        if topic_row["status"] in ("planned", "cut") and new in ("planned", "cut") and new != topic_row["status"]:
            db.update("plan_topics", user_id, topic_row["id"], {"status": new})

    kept = defaultdict(int)
    for t in pinned:
        kept[_d(t["date"])] += 1
    _store_horizon(db, user_id, plan["id"], built, kept)
    return db.update("plans", user_id, plan["id"], {
        "roadmap": built.schedule.roadmap.model_dump(mode="json"),
        "feasibility": built.feasibility.model_dump(),
        "refreshed_on": now.isoformat(),
    })


def _store_horizon(db: Database, user_id: str, plan_id: str, built: BuiltPlan, kept_per_day: dict) -> None:
    end = today() + timedelta(days=settings.PLANNER_HORIZON_DAYS)
    db.insert_many("plan_tasks", user_id, [{
        "plan_id": plan_id, "date": t.date.isoformat(), "position": t.position + kept_per_day.get(t.date, 0),
        "kind": t.kind, "subject": t.subject, "topic_id": t.topic_id, "title": t.title, "minutes": t.minutes,
        "details": t.details, "status": "todo",
    } for t in built.schedule.tasks if t.date < end])


def _ingest_interviews(db: Database, user_id: str, plan: dict) -> None:
    """Mock interviews done since the plan started: weak CS topics get a re-learn topic; strong ones close gaps."""
    scores = interview_topic_scores(db, user_id, after=plan["created_at"])
    existing = {r["topic_id"] for r in db.list("plan_topics", user_id, limit=500, plan_id=plan["id"])}
    labels = {s: sub.label for s, sub in load_curriculum().items()}
    for subject, score in scores.items():
        if score < 60 and f"{subject}.relearn" not in existing and any(t.startswith(f"{subject}.") for t in existing):
            db.insert("plan_topics", user_id, PlanTopic(
                topic_id=f"{subject}.relearn", subject=subject, priority="must", source="interview_gap", position=200,
                title=f"Re-learn weak {labels[subject]} topics from your mock interview",
                planned_minutes=RELEARN_MINUTES,
                details={"interview": {"track": "fundamentals", "topics": [subject]}},
            ).model_dump(mode="json") | {"plan_id": plan["id"]})
        if score >= 75:
            prefix = f"{CS_GAP_LABELS[subject]}:"
            for gap in open_gaps(db, user_id):
                if gap["source"] == "interview" and gap["skill"].startswith(prefix):
                    db.update("skill_gaps", user_id, gap["id"], {"resolved_at": utc_now()})


# ---------- Tasks ----------

def get_task(db: Database, user_id: str, task_id: str) -> dict:
    task = db.get("plan_tasks", user_id, task_id)
    if task is None:
        raise AppError("not_found", "Task not found", 404)
    return task


def update_task(db: Database, user_id: str, task_id: str, change: TaskUpdate) -> dict:
    task = get_task(db, user_id, task_id)
    old, new = task["status"], change.status
    if old == new:
        return task
    topic = db.find_one("plan_topics", user_id, plan_id=task["plan_id"], topic_id=task["topic_id"]) \
        if task["topic_id"] else None
    if topic and task["kind"] == "review":   # done or skipped, the review is over; undo puts it back
        stage = task["details"].get("stage", 1)
        review_stage = max(topic["review_stage"], stage) if new != "todo" else min(topic["review_stage"], stage - 1)
        db.update("plan_topics", user_id, topic["id"], {"review_stage": review_stage})
    elif topic:
        delta = task["minutes"] * ((new == "done") - (old == "done"))
        if delta:
            done = max(topic["done_minutes"] + delta, 0)
            finished = done >= topic["planned_minutes"]
            db.update("plan_topics", user_id, topic["id"], {
                "done_minutes": done,
                "status": "done" if finished else "in_progress" if done else "planned",
                "learned_on": (topic["learned_on"] or today().isoformat()) if finished else None,
            })
    return db.update("plan_tasks", user_id, task_id, {"status": new, "done_at": utc_now() if new == "done" else None})


def move_task(db: Database, user_id: str, task_id: str, day: date) -> dict:
    task = get_task(db, user_id, task_id)
    plan = db.get("plans", user_id, task["plan_id"])
    if task["status"] != "todo":
        raise AppError("not_movable", "Only tasks that are still to do can be moved.", 409)
    if not today() <= day <= _d(plan["target_date"]):
        raise AppError("bad_date", "Pick a day between today and your target date.", 422)
    profile = PlannerProfile.model_validate(plan["profile_snapshot"])
    others = [t for t in plan_tasks(db, user_id, plan["id"], day, day) if t["id"] != task_id]
    capacity = day_minutes(profile, day)
    if sum(t["minutes"] for t in others if t["status"] == "todo") + task["minutes"] > capacity:
        raise AppError("day_full", "That day is already full. Pick another day.", 409)
    return db.update("plan_tasks", user_id, task_id, {
        "date": day.isoformat(), "position": len(others), "details": {**task["details"], "pinned": True}})


# ---------- Check-in ----------

def checkin(db: Database, user_id: str, request: CheckinRequest) -> dict:
    plan = current_plan(db, user_id)
    now = today()
    week_start = now - timedelta(days=now.weekday() + 7)          # last week's Monday
    week = plan_tasks(db, user_id, plan["id"], week_start, week_start + timedelta(days=6))
    planned = sum(t["minutes"] for t in week)
    done = sum(t["minutes"] for t in week if t["status"] == "done")
    row = {"plan_id": plan["id"], "week_start": week_start.isoformat(), "planned_minutes": planned,
           "done_minutes": done, "difficulty": request.difficulty, "note": request.note}
    existing = db.find_one("plan_checkins", user_id, plan_id=plan["id"], week_start=week_start.isoformat())
    if existing:
        db.update("plan_checkins", user_id, existing["id"], row)
    else:
        db.insert("plan_checkins", user_id, row)

    update: dict = {}
    recent = [c for c in db.list("plan_checkins", user_id, limit=10, plan_id=plan["id"]) if c["planned_minutes"]][:2]
    if len(recent) == 2:   # plan with what you really do: 0.85 × your completion rate, between 0.4 and 0.85
        rate = sum(c["done_minutes"] / c["planned_minutes"] for c in recent) / 2
        update["capacity_factor"] = round(min(MAX_FACTOR, max(MIN_FACTOR, DEFAULT_FACTOR * rate)), 2)
    pace = {"too_hard": 1.15, "too_easy": 0.9}.get(request.difficulty)
    if pace:
        per_problem = min(60, max(20, plan["settings"]["minutes_per_problem"] * pace))
        update["settings"] = {**plan["settings"], "minutes_per_problem": per_problem}
    if request.busy:
        snapshot = PlannerProfile.model_validate(plan["profile_snapshot"])
        snapshot.busy = [*snapshot.busy, *request.busy][-20:]
        update["profile_snapshot"] = snapshot.model_dump(mode="json")
        save_profile(db, user_id, snapshot)
    if update:
        plan = db.update("plans", user_id, plan["id"], update)
    return refresh(db, user_id, plan)


def last_checkin_week(db: Database, user_id: str, plan_id: str) -> str | None:
    rows = db.list("plan_checkins", user_id, limit=1, plan_id=plan_id)
    return rows[0]["week_start"] if rows else None


def checkin_due(db: Database, user_id: str, plan: dict) -> bool:
    """A check-in is offered from the second week on, once per week."""
    now = today()
    last_monday = (now - timedelta(days=now.weekday() + 7)).isoformat()
    started = _d(plan["start_date"]) <= now - timedelta(days=now.weekday() + 7)
    return started and last_checkin_week(db, user_id, plan["id"]) != last_monday
