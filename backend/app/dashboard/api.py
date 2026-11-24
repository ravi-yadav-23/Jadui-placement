"""HTTP routes for the Today dashboard and account data (mounted at /api/v2)."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.db import Database, get_db
from app.dashboard import service
from app.dashboard.account import delete_all_data
from app.dashboard.schemas import DashboardOverview

router = APIRouter(tags=["dashboard-v2"])


@router.get("/dashboard", response_model=DashboardOverview)
def dashboard(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """Readiness (with its formula), setup checklist, next actions, today's tasks and recent activity."""
    return service.overview(db, user.id)


@router.delete("/me/data", status_code=204)
def delete_my_data(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """Delete everything you created: resumes (and files), JDs, analyses, interviews, plans, coach messages."""
    delete_all_data(db, user.id)
