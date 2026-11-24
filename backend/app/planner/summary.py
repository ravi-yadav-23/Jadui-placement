"""Read-only overview of the planner for the dashboard and coach chat."""

from __future__ import annotations

from datetime import timedelta

from app.core.db import Database
from app.planner import service
from app.planner.schemas import PlannerOverview


def overview(db: Database, user_id: str) -> PlannerOverview:
    plan = db.find_one("plans", user_id, status="active")
    if plan is None:
        return PlannerOverview(has_plan=False)
    if service.needs_refresh(db, user_id, plan):
        plan = service.refresh(db, user_id, plan)
    now = service.today()
    monday = now - timedelta(days=now.weekday())
    tasks = service.plan_tasks(db, user_id, plan["id"])
    week = [t for t in tasks if monday <= service._d(t["date"]) <= monday + timedelta(days=6)]

    done_days = {service._d(t["date"]) for t in tasks if t["status"] == "done"}
    day = now if now in done_days else now - timedelta(days=1)
    streak = 0
    while day in done_days:
        streak += 1
        day -= timedelta(days=1)

    upcoming = next((w for w in plan["roadmap"]["weeks"]
                     if service._d(w["week_start"]) >= monday and w["finishes"]), None)
    milestone = None
    if upcoming:
        milestone = f"Week of {service._d(upcoming['week_start']):%d %b}: finish {', '.join(upcoming['finishes'][:2])}"
    return PlannerOverview(
        has_plan=True,
        target_date=plan["target_date"],
        today=[t for t in tasks if service._d(t["date"]) == now],
        week_planned_minutes=sum(t["minutes"] for t in week),
        week_done_minutes=sum(t["minutes"] for t in week if t["status"] == "done"),
        streak_days=streak,
        on_track=plan["feasibility"].get("on_track", True),
        next_milestone=milestone,
    )
