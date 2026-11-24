"""HTTP routes for the resume screener (mounted at /api/v2).

Routes stay thin: read the request, call service.py, return a response model.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.db import Database, get_db
from app.resume import analysis, service
from app.resume.schemas import (
    AnalysisDetail,
    AnalysisSummary,
    CreateAnalysis,
    FileUrl,
    ResumeDetail,
    ResumeProfile,
    ResumeSummary,
)

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
        background.add_task(service.process_resume, db, user.id, row["id"], data, file.filename or "")
    else:
        response.status_code = 200  # identical file already uploaded: nothing new to process
    return row


@router.get("/resumes", response_model=list[ResumeSummary])
def list_resumes(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return db.list("resumes", user.id, columns=RESUME_LIST_COLUMNS)


@router.get("/resumes/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return service.get_resume(db, user.id, resume_id)


@router.patch("/resumes/{resume_id}/profile", response_model=ResumeDetail)
def update_profile(
    resume_id: str,
    profile: ResumeProfile,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    return service.update_profile(db, user.id, resume_id, profile)


@router.get("/resumes/{resume_id}/file", response_model=FileUrl)
def get_resume_file(resume_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    row = service.get_resume(db, user.id, resume_id)
    return {"url": db.signed_url(row["storage_path"])}


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    service.delete_resume(db, user.id, resume_id)


# ---------- Analyses ----------

ANALYSIS_LIST_COLUMNS = "id,resume_id,jd_id,mode,target_role,status,error,overall_score,created_at,completed_at"


@router.post("/analyses", status_code=202, response_model=AnalysisSummary)
def create_analysis(
    request: CreateAnalysis,
    background: BackgroundTasks,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    row, is_new = analysis.create_analysis(db, user.id, request)
    if is_new:
        background.add_task(analysis.run_analysis, db, user.id, row["id"])
    else:
        response.status_code = 200  # cached result for identical inputs
    return row


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(
    resume_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    filters = {"resume_id": resume_id} if resume_id else {}
    return db.list("resume_analyses", user.id, columns=ANALYSIS_LIST_COLUMNS, **filters)


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return analysis.get_analysis(db, user.id, analysis_id)
