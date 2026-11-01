"""API Routes for GitHub PR Code Review."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, ConfigDict
from .services import service
from app.core.security import get_current_user

router = APIRouter(tags=["github-review"])

class PRReviewRequest(BaseModel):
    repo_url: str # e.g. https://github.com/owner/repo
    pr_number: int
    model_config = ConfigDict(extra="ignore")

class RepoAnalysisRequest(BaseModel):
    repo_url: str
    model_config = ConfigDict(extra="ignore")

@router.post("/github/review/pr")
async def review_pull_request(payload: PRReviewRequest, user: dict = Depends(get_current_user)):
    """Triggers an AI code review for a given GitHub PR."""
    try:
        parts = payload.repo_url.rstrip("/").split("/")
        if len(parts) < 2:
             raise HTTPException(status_code=400, detail="Invalid GitHub Repository URL")
        repo, owner = parts[-1], parts[-2]
        
        diff_text = await service.fetch_pr_diff(owner, repo, payload.pr_number)
        analysis = await service.analyze_diff(diff_text)
        saved = service.save_review(user["sub"], owner, repo, payload.pr_number, analysis)
        return {"review": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/github/analyze/repo")
async def analyze_repository(payload: RepoAnalysisRequest, user: dict = Depends(get_current_user)):
    """Triggers a project-wide architecture review."""
    try:
        parts = payload.repo_url.rstrip("/").split("/")
        if len(parts) < 2:
             raise HTTPException(status_code=400, detail="Invalid GitHub Repository URL")
        repo, owner = parts[-1], parts[-2]
        
        metadata = await service.fetch_repo_metadata(owner, repo)
        analysis = await service.analyze_repo(metadata)
        saved = service.save_repo_analysis(user["sub"], owner, repo, analysis)
        return {"analysis": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/github/review/history")
def get_user_review_history(limit: int = 10, user: dict = Depends(get_current_user)):
    return {"history": service.get_history(user["sub"], limit)}

@router.get("/github/analyze/history")
def get_repo_analysis_history(limit: int = 10, user: dict = Depends(get_current_user)):
    return {"history": service.get_repo_history(user["sub"], limit)}
