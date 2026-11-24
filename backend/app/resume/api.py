"""HTTP routes for the resume screener (mounted at /api/v2).

Routes stay thin: read the request, call service.py, return a response model.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.db import Database, get_db
from app.resume import service
from app.resume.schemas import FileUrl, ResumeDetail, ResumeSummary

router = APIRouter(tags=["resume-v2"])

# Large text columns are left out of list views.
RESUME_LIST_COLUMNS = "id,title,mime_type,page_count,status,error,profile_edited,created_at"


@router.post("/resumes", status_code=202, response_model=ResumeSummary)
async def upload_resume(
    background: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    data = await file.read(settings.RESUME_MAX_BYTES + 1)  # +1 so "too large" is detectable
    row, is_new = service.create_resume(db, user.id, file.filename or "", data, title)
    if is_new:
        background.add_task(service.process_resume, db, user.id, row["id"], data)
    else:
        response.status_code = 200  # identical file already uploaded: nothing new to process
    return row


@router.get("/resumes", response_model=list[ResumeSummary])
def list_resumes(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return db.list("resumes", user.id, columns=RESUME_LIST_COLUMNS)


@router.get("/resumes/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return service.get_resume(db, user.id, resume_id)


@router.get("/resumes/{resume_id}/file", response_model=FileUrl)
def get_resume_file(resume_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    row = service.get_resume(db, user.id, resume_id)
    return {"url": db.signed_url(row["storage_path"])}


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    service.delete_resume(db, user.id, resume_id)
