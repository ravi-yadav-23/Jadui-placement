"""What the coach knows about you: a compact JSON built on the server from every pillar.

The LLM never queries the database itself; it only sees this snapshot. Task ids in it are the only ids the
coach may use in actions (checked in service.py).
"""

from __future__ import annotations

from datetime import timedelta

from app.core.db import Database
from app.dashboard.service import overview as dashboard_overview
from app.planner import service as planner


def build_context(db: Database, user_id: str) -> dict:
    today = planner.today()
    dashboard = dashboard_overview(db, user_id)
    context: dict = {
        "today": today.isoformat(),
        "readiness": {"score": dashboard.readiness.score,
                      "parts": {p.label: p.value for p in dashboard.readiness.parts}},
        "open_gaps": [g.skill for g in dashboard.open_gaps],
        "suggested_next": [a.label for a in dashboard.next_actions],
    }

    profile_row = db.find_one("planner_profiles", user_id)
    if profile_row:
        a = profile_row["answers"]
        keep = ("status", "year", "experience_years", "target_role", "target_level", "company_types", "target_date",
                "weekday_hours", "weekend_hours", "language")
        context["profile"] = {k: a.get(k) for k in keep if a.get(k) is not None}

    plan = db.find_one("plans", user_id, status="active")
    if plan:
        upcoming = planner.plan_tasks(db, user_id, plan["id"], today, today + timedelta(days=7))
        context["plan"] = {
            "target_date": str(plan["target_date"]),
            "on_track": plan["feasibility"].get("on_track", True),
            "not_included": plan["feasibility"].get("cut", [])[:5],
            "phase_now": next((p["name"] for p in plan["roadmap"]["phases"]
                               if str(p["start"]) <= today.isoformat() <= str(p["end"])), None),
            "next_milestones": [{"week": str(w["week_start"]), "finishes": w["finishes"][:3]}
                                for w in plan["roadmap"]["weeks"]
                                if str(w["week_start"]) >= (today - timedelta(days=today.weekday())).isoformat()
                                and w["finishes"]][:3],
            "tasks": [{"id": t["id"], "date": str(t["date"])[:10], "title": t["title"], "minutes": t["minutes"],
                       "status": t["status"]} for t in upcoming][:25],
        }

    review = next((a for a in db.list("resume_analyses", user_id, columns="mode,status,overall_score,result,created_at",
                                      limit=10) if a["status"] == "done" and a["mode"] == "general"), None)
    if review:
        context["latest_resume_review"] = {"score": review["overall_score"],
                                           "top_actions": (review.get("result") or {}).get("top_actions", [])[:3]}

    interview = next((i for i in db.list("interviews", user_id, columns="track,status,score,report,created_at",
                                         limit=10) if i["status"] == "completed" and i.get("report")), None)
    if interview:
        report = interview["report"]
        context["latest_interview"] = {"track": interview["track"], "score": interview["score"],
                                       "topics": report.get("topics", {}), "dimensions": report.get("dimensions", {}),
                                       "gaps": report.get("gaps", [])[:4]}
    context["interview_trend"] = dashboard.interview_trend
    return context
