"""HTTP routes for mock interviews (mounted at /api/v2). Thin: parse, call service.py, return."""

from fastapi import APIRouter, BackgroundTasks, Depends, Response

from app.core.auth import CurrentUser, get_current_user
from app.core.db import Database, get_db
from app.interview import service, summary
from app.interview.schemas import (
    AnswerRequest,
    CreateInterview,
    InterviewDetail,
    InterviewOverview,
    InterviewSummary,
)

router = APIRouter(tags=["interview-v2"])

LIST_COLUMNS = "id,track,mode,status,target_role,score,error,created_at,completed_at"


def _detail(db: Database, user_id: str, interview_id: str) -> dict:
    return service.view(*service.load(db, user_id, interview_id))


@router.post("/interviews", status_code=202, response_model=InterviewDetail)
def create_interview(
    request: CreateInterview,
    background: BackgroundTasks,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    row, needs_planning = service.create_interview(db, user.id, request)
    if needs_planning:
        background.add_task(service.plan_interview, db, user.id, row["id"])
    else:
        response.status_code = 201  # bank-only tracks start immediately
    return _detail(db, user.id, row["id"])


@router.get("/interviews", response_model=list[InterviewSummary])
def list_interviews(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return db.list("interviews", user.id, columns=LIST_COLUMNS)


@router.get("/interviews/{interview_id}", response_model=InterviewDetail)
def get_interview(interview_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    return _detail(db, user.id, interview_id)


@router.post("/interviews/{interview_id}/turns/{turn_id}/answer", status_code=202, response_model=InterviewDetail)
def answer(
    interview_id: str,
    turn_id: str,
    request: AnswerRequest,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    service.submit_answer(db, user.id, interview_id, turn_id, request)
    background.add_task(service.evaluate_turn, db, user.id, interview_id, turn_id)
    return _detail(db, user.id, interview_id)


@router.post("/interviews/{interview_id}/turns/{turn_id}/retry", status_code=202, response_model=InterviewDetail)
def retry(
    interview_id: str,
    turn_id: str,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    service.retry_turn(db, user.id, interview_id, turn_id)
    background.add_task(service.evaluate_turn, db, user.id, interview_id, turn_id)
    return _detail(db, user.id, interview_id)


@router.post("/interviews/{interview_id}/skip", response_model=InterviewDetail)
def skip(interview_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    service.skip(db, user.id, interview_id)
    return _detail(db, user.id, interview_id)


@router.post("/interviews/{interview_id}/finish", response_model=InterviewDetail)
def finish(interview_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    service.finish(db, user.id, interview_id)
    return _detail(db, user.id, interview_id)


@router.delete("/interviews/{interview_id}", status_code=204)
def delete(interview_id: str, user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    service.delete_interview(db, user.id, interview_id)


@router.get("/interview/summary", response_model=InterviewOverview)
def interview_summary(user: CurrentUser = Depends(get_current_user), db: Database = Depends(get_db)):
    """Recent scores, topic averages and open gaps, for the dashboard, planner and coach chat."""
    return summary.overview(db, user.id)
