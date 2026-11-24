"""Shapes for the coach chat."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

Page = Literal["today", "planner", "roadmap", "interview", "resume", "settings"]


class CoachAction(BaseModel):
    """Something the coach proposes. It runs only when the student clicks the button (human in the loop)."""
    type: Literal["open_page", "start_interview", "mark_task_done", "move_task", "replan"]
    label: str = Field(description="Button text, at most 6 words")
    page: Page | None = Field(None, description="open_page only")
    task_id: str | None = Field(None, description="mark_task_done / move_task: an id from the context's tasks")
    date: dt.date | None = Field(None, description="move_task only: the new date")
    track: Literal["mixed", "resume", "jd", "fundamentals", "behavioral"] | None = Field(
        None, description="start_interview only")
    topics: list[Literal["os", "dbms", "cn", "oop"]] = Field(default_factory=list,
                                                           description="start_interview with fundamentals")


class CoachDraft(BaseModel):
    """LLM contract for coach.v1."""
    reply: str = Field(description="The answer to the student, plain text, at most about 150 words")
    actions: list[CoachAction] = Field(default_factory=list, description="0-3 proposed actions")


class CoachMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    actions: list[CoachAction] = Field(default_factory=list)
    created_at: str


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
