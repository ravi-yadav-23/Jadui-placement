"""The "Today" dashboard: one read-only view over every pillar.

Readiness = weighted mean of the parts that have data (at least 2 parts, otherwise "not enough data"):
    resume      latest general review score                                  weight 25
    interviews  average of your last 3 mock interviews                       weight 35
    plan        share of planned study minutes done in the last 14 days      weight 25
    gaps        share of skill gaps you have closed                          weight 15
Every part is shown with its value and where it comes from, so the number is never a mystery.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from app.core.db import Database
from app.dashboard.schemas import (
    ActivityItem,
    DashboardOverview,
    GapItem,
    NextAction,
    Readiness,
    ReadinessPart,
    SetupStep,
)
from app.interview.summary import overview as interview_overview
from app.planner import service as planner
from app.planner.summary import overview as planner_overview
from app.resume.summary import overview as resume_overview

WEIGHTS = {"resume": 25, "interviews": 35, "plan": 25, "gaps": 15}
FORMULA = ("Weighted average of the parts that have data: resume review 25%, mock interviews 35%, "
           "study plan completion (last 14 days) 25%, skill gaps closed 15%. Needs at least two parts.")
TRACK_NAMES = {"mixed": "mixed round", "resume": "resume deep-dive", "jd": "job description",
               "fundamentals": "CS fundamentals", "behavioral": "HR / behavioral"}


def overview(db: Database, user_id: str) -> DashboardOverview:
    resume = resume_overview(db, user_id)
    interviews = interview_overview(db, user_id)
    plan_summary = planner_overview(db, user_id)
    plan = db.find_one("plans", user_id, status="active")
    gaps = db.list("skill_gaps", user_id, columns="skill,source,resolved_at,created_at", limit=300)

    latest_review = next((a.overall_score for a in resume.recent if a.mode == "general"), None)
    last_three = [r.score for r in interviews.recent[:3]]
    plan_rate = _plan_completion(db, user_id, plan)
    closed = sum(1 for g in gaps if g.get("resolved_at"))
    parts = [
        ReadinessPart(key="resume", label="Resume", weight=WEIGHTS["resume"], value=latest_review,
                      detail="Latest general review" if latest_review is not None else "No review yet"),
        ReadinessPart(key="interviews", label="Interviews", weight=WEIGHTS["interviews"],
                      value=round(sum(last_three) / len(last_three)) if last_three else None,
                      detail=f"Average of your last {len(last_three)}" if last_three else "No mock interview yet"),
        ReadinessPart(key="plan", label="Study plan", weight=WEIGHTS["plan"], value=plan_rate,
                      detail="Planned minutes done, last 14 days" if plan_rate is not None else "No tasks due yet"),
        ReadinessPart(key="gaps", label="Gaps closed", weight=WEIGHTS["gaps"],
                      value=round(100 * closed / len(gaps)) if gaps else None,
                      detail=f"{closed} of {len(gaps)} closed" if gaps else "No gaps found yet"),
    ]
    scored = [p for p in parts if p.value is not None]
    score = round(sum(p.value * p.weight for p in scored) / sum(p.weight for p in scored)) if len(scored) >= 2 else None

    open_gaps = [g for g in gaps if not g.get("resolved_at")]
    return DashboardOverview(
        readiness=Readiness(score=score, parts=parts, formula=FORMULA),
        setup=_setup(resume.resume_count, interviews.completed_count, plan is not None, latest_review is not None),
        next_actions=_next_actions(db, user_id, plan, plan_summary, resume.resume_count, latest_review,
                                   interviews.recent),
        today=plan_summary,
        interview_trend=[r.score for r in reversed(interviews.recent[:8])],
        latest_resume_score=latest_review,
        open_gaps=[GapItem(skill=s, source=src) for s, src in {g["skill"]: g["source"] for g in open_gaps}.items()][:8],
        activity=_activity(db, user_id, plan),
    )


def _plan_completion(db: Database, user_id: str, plan: dict | None) -> int | None:
    if plan is None:
        return None
    today = planner.today()
    window = planner.plan_tasks(db, user_id, plan["id"], today - timedelta(days=14), today - timedelta(days=1))
    planned = sum(t["minutes"] for t in window)
    if not planned:
        return None
    return round(100 * sum(t["minutes"] for t in window if t["status"] == "done") / planned)


def _setup(resumes: int, interviews: int, has_plan: bool, reviewed: bool) -> list[SetupStep]:
    return [
        SetupStep(key="plan", label="Create your study plan", done=has_plan, href="/dashboard/planner/setup"),
        SetupStep(key="resume", label="Upload your resume", done=resumes > 0, href="/dashboard/resume"),
        SetupStep(key="review", label="Get a resume review", done=reviewed, href="/dashboard/resume"),
        SetupStep(key="interview", label="Take your first mock interview", done=interviews > 0,
                  href="/dashboard/interview"),
    ]


def _next_actions(db, user_id, plan, plan_summary, resumes, latest_review, recent_interviews) -> list[NextAction]:
    actions = []
    left = [t for t in plan_summary.today if t.status == "todo"]
    if left:
        minutes = sum(t.minutes for t in left)
        actions.append(NextAction(label=f"Finish today's {len(left)} task{'s' if len(left) > 1 else ''}",
                                  href="/dashboard/planner", reason=f"About {minutes} minutes left today"))
    if plan is not None and planner.checkin_due(db, user_id, plan):
        actions.append(NextAction(label="Do your weekly check-in", href="/dashboard/planner",
                                  reason="Two minutes; it keeps your plan realistic"))
    if plan is None:
        actions.append(NextAction(label="Create your study plan", href="/dashboard/planner/setup",
                                  reason="Everything else builds on it"))
    if resumes == 0:
        actions.append(NextAction(label="Upload your resume", href="/dashboard/resume",
                                  reason="Gets you a parse check and a review"))
    elif latest_review is None:
        actions.append(NextAction(label="Run a resume review", href="/dashboard/resume",
                                  reason="See which bullets need work"))
    last = recent_interviews[0].created_at if recent_interviews else None
    if last is None or last < (planner.today() - timedelta(days=7)).isoformat():
        actions.append(NextAction(label="Take a mock interview", href="/dashboard/interview",
                                  reason="None in the last 7 days" if last else "Find your weak topics early"))
    return actions[:4]


def _activity(db: Database, user_id: str, plan: dict | None) -> list[ActivityItem]:
    items: list[ActivityItem] = []
    for a in db.list("resume_analyses", user_id, columns="id,mode,status,overall_score,completed_at,created_at",
                     limit=10):
        if a["status"] == "done":
            name = "JD match" if a["mode"] == "jd" else "Resume review"
            items.append(ActivityItem(kind="resume", title=f"{name}: {a['overall_score']}/100",
                                      at=a.get("completed_at") or a["created_at"],
                                      href=f"/dashboard/resume/analysis/{a['id']}"))
    for i in db.list("interviews", user_id, columns="id,track,status,score,completed_at,created_at", limit=10):
        if i["status"] == "completed":
            track = TRACK_NAMES.get(i["track"], i["track"])
            items.append(ActivityItem(kind="interview", title=f"Mock interview ({track}): {i['score']}/100",
                                      at=i.get("completed_at") or i["created_at"],
                                      href=f"/dashboard/interview/{i['id']}"))
    if plan is not None:
        items.append(ActivityItem(kind="plan", title="Created your study plan", at=plan["created_at"],
                                  href="/dashboard/planner"))
        per_day: dict[str, list[int]] = defaultdict(list)
        since = planner.today() - timedelta(days=7)
        for t in planner.plan_tasks(db, user_id, plan["id"], since, planner.today()):
            if t["status"] == "done":
                per_day[str(t["date"])[:10]].append(t["minutes"])
        for day, minutes in per_day.items():
            items.append(ActivityItem(kind="tasks", at=f"{day}T23:59:00",
                                      title=f"Finished {len(minutes)} study task{'s' if len(minutes) > 1 else ''} "
                                            f"({sum(minutes)} min)", href="/dashboard/planner"))
    return sorted(items, key=lambda item: item.at, reverse=True)[:8]
