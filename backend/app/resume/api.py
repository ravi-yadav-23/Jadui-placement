"""HTTP routes for the resume screener (mounted at /api/v2)."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.db import Database, get_db

router = APIRouter(tags=["resume-v2"])

# Large text columns are left out of list views.
RESUME_LIST_COLUMNS = "id,title,mime_type,page_count,status,error,profile_edited,created_at"


@router.get("/resumes")
def list_resumes(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)) -> list[dict]:
    return db.list("resumes", user.id, columns=RESUME_LIST_COLUMNS)
