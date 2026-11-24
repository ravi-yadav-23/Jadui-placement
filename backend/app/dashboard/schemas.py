"""Shapes for the Today dashboard."""

from __future__ import annotations

from pydantic import BaseModel

from app.planner.schemas import PlannerOverview


class ReadinessPart(BaseModel):
    key: str
    label: str
    value: int | None          # 0-100, or None when there is no data yet
    weight: int
    detail: str


class Readiness(BaseModel):
    score: int | None
    parts: list[ReadinessPart]
    formula: str


class SetupStep(BaseModel):
    key: str
    label: str
    done: bool
    href: str


class NextAction(BaseModel):
    label: str
    href: str
    reason: str


class ActivityItem(BaseModel):
    kind: str                  # resume | interview | plan | tasks
    title: str
    at: str
    href: str | None = None


class GapItem(BaseModel):
    skill: str
    source: str


class DashboardOverview(BaseModel):
    readiness: Readiness
    setup: list[SetupStep]
    next_actions: list[NextAction]
    today: PlannerOverview
    interview_trend: list[int]          # oldest -> newest
    latest_resume_score: int | None
    open_gaps: list[GapItem]
    activity: list[ActivityItem]
