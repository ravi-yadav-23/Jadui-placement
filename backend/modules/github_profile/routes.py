"""GitHub profile analytics API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Depends

from .services import build_profile, can_load_quick
from app.core.security import get_current_user

router = APIRouter(tags=["github-profile"])


@router.get("/github/can-load")
def github_can_load(user: str = Query(..., min_length=1, max_length=39)) -> dict[str, Any]:
    return {"ok": can_load_quick(user)}


@router.get("/github/profile")
def github_profile(
    username: str = Query(..., min_length=1, max_length=39),
    insights: bool = Query(False, description="Include Gemini summary when GEMINI_API_KEY is set"),
    user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    profile = build_profile(username, include_insights=insights)
    
    # Sync with global state
    try:
        from modules.system_ai.sync import sync_github_insights
        sync_github_insights(user["sub"], profile)
    except Exception as e:
        print(f"GitHub synchronization skipped: {e}")
            
    return profile
