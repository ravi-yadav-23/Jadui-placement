"""Routes for persisting generated system state."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ConfigDict

from .services import service
from .intelligence import intelligence_service
from app.core.security import get_current_user

router = APIRouter(tags=["system-ai"])


class TaskItem(BaseModel):
    id: str
    title: str
    category: str = "Core"
    completed: bool = False
    due: str = "This Week"


class RoadmapDay(BaseModel):
    day: str
    date: str
    status: str = "upcoming"
    tasks: list[str] = Field(default_factory=list)


class NotificationItem(BaseModel):
    id: str = ""
    title: str
    body: str
    read: bool = False


class ChatContextModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    avgResumeScore: int = 0
    avgInterviewScore: int = 0
    topSkillGaps: list[str] = Field(default_factory=list)
    latestRoleTarget: str = ""
    targetRole: str = ""
    targetPlacementDate: str = ""


class SaveSystemStateRequest(BaseModel):
    tasks: list[TaskItem] = Field(default_factory=list)
    roadmap: list[RoadmapDay] = Field(default_factory=list)
    notifications: list[NotificationItem] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    chat_context: ChatContextModel = Field(default_factory=ChatContextModel)
    chat_history: list[dict] = Field(default_factory=list)
    chat_sessions: list[dict] = Field(default_factory=list)
    active_chat_session_id: str = ""
    model_config = ConfigDict(extra="ignore")


class MarkNotificationReadRequest(BaseModel):
    notification_id: str
    model_config = ConfigDict(extra="ignore")


class RegenerateRoadmapRequest(BaseModel):
    skill_gaps: list[str] | None = None
    model_config = ConfigDict(extra="ignore")


@router.get("/system/state")
def get_system_state(user: dict = Depends(get_current_user)) -> dict:
    return {"state": service.get_state(user["sub"])}


@router.post("/system/state")
def save_system_state(payload: SaveSystemStateRequest, user: dict = Depends(get_current_user)) -> dict:
    return {
        "state": service.save_state(
            user_id=user["sub"],
            tasks=[item.model_dump() for item in payload.tasks],
            roadmap=[item.model_dump() for item in payload.roadmap],
            notifications=[item.model_dump() for item in payload.notifications],
            skill_gaps=payload.skill_gaps,
            chat_context=payload.chat_context.model_dump(),
            chat_history=payload.chat_history,
            chat_sessions=payload.chat_sessions,
            active_chat_session_id=payload.active_chat_session_id,
        )
    }


@router.post("/system/notifications/read")
def mark_notification_read(payload: MarkNotificationReadRequest, user: dict = Depends(get_current_user)) -> dict:
    return {"state": service.mark_notification_read(user["sub"], payload.notification_id)}


@router.post("/system/roadmap/regenerate")
def regenerate_roadmap(payload: RegenerateRoadmapRequest, user: dict = Depends(get_current_user)) -> dict:
    return {"state": service.regenerate_roadmap(user["sub"], payload.skill_gaps)}


@router.get("/system/readiness")
def get_readiness_scorecard(user: dict = Depends(get_current_user)):
    return intelligence_service.get_readiness_radar(user["sub"])


@router.get("/system/insights")
def get_system_insights(user: dict = Depends(get_current_user)):
    """Aggregates all AI metrics for the student dashboard."""
    radar = intelligence_service.get_readiness_radar(user["sub"])
    return {
        "radar": radar,
        "avgScore": int(sum(radar.values()) / len(radar)) if radar else 0,
        "readinessTier": "INTERVIEW_READY" if (radar.get('interview') or 0) > 70 else "BUILD_MODE"
    }
