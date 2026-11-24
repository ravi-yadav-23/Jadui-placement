"""Pydantic models for the resume screener.

Two kinds live here:
  * LLM contracts  - shapes the model must return (validated by app/llm/client.py)
  * API responses  - shapes the frontend receives (they also generate the TypeScript types)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["queued", "processing", "ready", "failed"]


# ---------- Parse health ----------

class Check(BaseModel):
    id: str
    status: Literal["pass", "warn", "fail", "info"]
    message: str
    fix: str | None = None


class Contacts(BaseModel):
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    leetcode: str | None = None
    portfolio: str | None = None


# ---------- API responses ----------

class ResumeSummary(BaseModel):
    id: str
    title: str
    mime_type: str
    page_count: int
    status: Status
    error: str | None = None
    profile_edited: bool = False
    created_at: str


class ResumeDetail(ResumeSummary):
    raw_text: str | None = None
    extract_meta: dict = Field(default_factory=dict)
    checks: list[Check] = Field(default_factory=list)
    contacts: Contacts = Field(default_factory=Contacts)


class FileUrl(BaseModel):
    url: str
