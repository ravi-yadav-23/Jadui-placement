"""HTTP routes for the planner (mounted at /api/v2). Thin: parse, call service.py, return."""

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.db import Database, get_db
from app.planner import service, summary
from app.planner.builder import BuiltPlan
from app.planner.schemas import (
    CheckinRequest,
    PlanDetail,
    PlannerOverview,
    PlannerProfile,
    PlanPreview,
    ProfileResponse,
    TaskMove,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(tags=["planner-v2"])


def _preview(built: BuiltPlan) -> dict:
    weeks = max((built.target - built.start).days + 1, 1) / 7
    return {"start_date": built.start, "target_date": built.target, "weeks": round(weeks, 1),
            "hours_per_week": round(built.usable_minutes / 60 / weeks, 1), "allocation": built.allocation,
            "feasibility": built.feasibility, "roadmap": built.schedule.roadmap}


def _detail(db: Database, user_id: str, plan: dict) -> dict:
    return {**service.plan_view(db, user_id, plan), "checkin_due": service.checkin_due(db, user_id, plan)}


@router.get("/planner/profile", response_model=ProfileResponse)
def get_profile(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """Saved answers (if any) plus suggestions from your resume, gaps and mock interviews."""
    return service.get_profile(db, user.id)


@router.put("/planner/profile", response_model=PlannerProfile)
def save_profile(profile: PlannerProfile, user: CurrentUser = Depends(get_current_user),
                 db: Database = Depends(get_db)):
    return service.save_profile(db, user.id, profile)


@router.post("/plans/preview", response_model=PlanPreview)
def preview(profile: PlannerProfile, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """What the plan would look like (fits or not, subject mix, phases) without saving anything."""
    return _preview(service.preview(db, user.id, profile))


@router.post("/plans", status_code=201, response_model=PlanDetail)
def create_plan(profile: PlannerProfile, background: BackgroundTasks,
                user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    plan = service.create_plan(db, user.id, profile)
    background.add_task(service.write_plan_text, db, user.id, plan["id"])
    return _detail(db, user.id, plan)


@router.get("/plans/current", response_model=PlanDetail)
def current(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    plan = service.current_plan(db, user.id)
    if service.needs_refresh(db, user.id, plan):
        plan = service.refresh(db, user.id, plan)
    return _detail(db, user.id, plan)


@router.get("/plans/current/tasks", response_model=list[TaskOut])
def tasks(start: date | None = None, end: date | None = None,
          user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    plan = service.current_plan(db, user.id)
    return service.plan_tasks(db, user.id, plan["id"], start, end)


@router.post("/plans/current/replan", response_model=PlanDetail)
def replan(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    plan = service.refresh(db, user.id, service.current_plan(db, user.id))
    return _detail(db, user.id, plan)


@router.post("/plans/current/checkins", response_model=PlanDetail)
def checkin(request: CheckinRequest, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return _detail(db, user.id, service.checkin(db, user.id, request))


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, change: TaskUpdate, user: CurrentUser = Depends(get_current_user),
                db: Database = Depends(get_db)):
    return service.update_task(db, user.id, task_id, change)


@router.post("/tasks/{task_id}/move", response_model=TaskOut)
def move_task(task_id: str, move: TaskMove, user: CurrentUser = Depends(get_current_user),
              db: Database = Depends(get_db)):
    return service.move_task(db, user.id, task_id, move.date)


@router.get("/planner/summary", response_model=PlannerOverview)
def planner_summary(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """Today's tasks, this week's progress, streak and next milestone, for the dashboard and coach."""
    return summary.overview(db, user.id)
