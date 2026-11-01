"""FastAPI routes for Resume Intelligence Engine."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, Depends
from pydantic import BaseModel, Field, ConfigDict

from .services import service
from app.core.security import get_current_user


router = APIRouter(tags=["resume-ai"])


class AnalyzeResumeRequest(BaseModel):
    file_id: str
    role_target: str = Field(default="Software Engineer")
    target_skills: list[str] = Field(default_factory=list)
    use_llm: bool = True
    model_config = ConfigDict(extra="ignore")


@router.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> dict:
    from fastapi import HTTPException
    
    # MIME Type Validation
    allowed_mimes = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_mimes:
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Only PDF and Word documents are allowed.")
        
    # File Size Validation (Max 5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5MB.")

    record = await service.upload_resume(file, user["sub"])
    # Ideally, the service should tag this file_id with user["sub"]
    return {
        "file_id": record.file_id,
        "filename": record.filename,
        "candidate_name": record.candidate_name,
        "text_preview": record.text[:500],
    }


@router.post("/resume/analyze")
def analyze_resume(payload: AnalyzeResumeRequest, user: dict = Depends(get_current_user)) -> dict:
    result = service.analyze_resume(
        user_id=user["sub"],
        file_id=payload.file_id,
        role_target=payload.role_target,
        target_skills=payload.target_skills,
        use_llm=payload.use_llm,
    )
    return {"result_id": result.result_id, "analysis": result.__dict__}


class PatchResumeRequest(BaseModel):
    result_id: str
    add_strengths: list[str] = Field(default_factory=list)


@router.patch("/resume/result")
def patch_resume_result(payload: PatchResumeRequest, user: dict = Depends(get_current_user)) -> dict:
    """
    Updates an existing resume results with AI-enhanced suggestions.
    """
    result = service.patch_result(
        result_id=payload.result_id,
        add_strengths=payload.add_strengths,
        user_id=user["sub"],
    )
    return {"status": "updated", "result": result.__dict__}

@router.get("/resume/result")
def get_resume_result(result_id: str, user: dict = Depends(get_current_user)) -> dict:
    result = service.get_result(result_id, user["sub"])
    return {"result": result.__dict__}


@router.get("/resume/history")
def get_resume_history(limit: int = 10, user: dict = Depends(get_current_user)) -> dict:
    return {"history": service.get_history(user_id=user["sub"], limit=limit)}
