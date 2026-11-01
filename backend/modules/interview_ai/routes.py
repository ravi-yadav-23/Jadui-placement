"""FastAPI routes for AI Interview module."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from fastapi import APIRouter, Depends
from typing import Any

from .services import service
from app.core.security import get_current_user


router = APIRouter(tags=["interview-ai"])


class StartInterviewRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=100)
    skills: list[str] = Field(default_factory=list)
    level: str = Field(default="not specified")
    interview_type: str = Field(default="mixed")
    question_count: int = Field(default=5, ge=1, le=20)


class FeedbackRequest(BaseModel):
    interviewId: str
    transcript: list[dict[str, Any]]
    model_config = ConfigDict(extra="ignore")


class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_index: int
    answer: str


@router.post("/interview/feedback")
def generate_feedback(payload: FeedbackRequest, user: dict = Depends(get_current_user)) -> dict:
    """
    Analyzes the full transcript from a live session.
    Triggers global sync for skill gaps found during the conversation.
    """
    result = service.generate_feedback_from_transcript(
        session_id=payload.interviewId,
        user_id=user["sub"],
        transcript=payload.transcript
    )
    
    # Sync triggers are handled inside the service method
    return {"feedback": result}


@router.post("/interview/start")
def start_interview(payload: StartInterviewRequest, user: dict = Depends(get_current_user)) -> dict:
    session = service.start_interview(
        role=payload.role,
        skills=payload.skills,
        level=payload.level,
        interview_type=payload.interview_type,
        question_count=payload.question_count,
        user_id=user["sub"],
    )
    return session


@router.post("/interview/answer")
def submit_answer(payload: SubmitAnswerRequest, user: dict = Depends(get_current_user)) -> dict:
    result = service.submit_answer(
        session_id=payload.session_id,
        question_index=payload.question_index,
        answer=payload.answer,
        user_id=user["sub"],
    )
    return {"evaluation": result.__dict__}


@router.get("/interview/result")
def interview_result(session_id: str, user: dict = Depends(get_current_user)) -> dict:
    result = service.get_result(session_id=session_id, user_id=user["sub"])
    
    # Sync with global state
    try:
        from modules.system_ai.sync import sync_interview_insights
        # Collect all gaps from individual evaluations
        all_gaps = []
        evals = result.get("evaluations", [])
        for e in evals:
            all_gaps.extend(e.get("gaps", []))
        
        if all_gaps:
            sync_interview_insights(user["sub"], list(set(all_gaps))[:5])
    except Exception as e:
        print(f"Interview synchronization failed: {e}")
            
    return result


@router.get("/interview/history")
def interview_history(limit: int = 10, user: dict = Depends(get_current_user)) -> dict:
    return {"history": service.get_history(user_id=user["sub"], limit=limit)}
