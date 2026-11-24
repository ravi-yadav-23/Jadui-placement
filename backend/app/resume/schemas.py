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


# ---------- Structured profile ----------
# The LLM fills the *Draft* models (plain strings, no IDs). Our code then converts the draft
# into ResumeProfile: it assigns stable bullet IDs and checks every bullet against the raw text.

class EntryDraft(BaseModel):
    title: str = Field(description="Role title for a job, or the project name")
    org: str | None = Field(None, description="Company / organisation; null for personal projects")
    location: str | None = None
    start: str | None = Field(None, description="Start date exactly as written, e.g. 'Jun 2025'")
    end: str | None = Field(None, description="End date exactly as written, e.g. 'Aug 2025' or 'Present'")
    tech: list[str] = Field(default_factory=list, description="Technologies explicitly listed for this entry")
    bullets: list[str] = Field(default_factory=list, description="Bullet points copied verbatim")


class EducationDraft(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start: str | None = None
    end: str | None = None
    grad_year: int | None = Field(None, description="Graduation year as a number, e.g. 2026")
    cgpa: float | None = Field(None, description="CGPA/GPA as a number, e.g. 8.4")
    cgpa_scale: float | None = Field(None, description="Scale of the CGPA, e.g. 10 or 4")


class ProfileDraft(BaseModel):
    headline: str | None = Field(None, description="Title line under the name, if any")
    summary: str | None = None
    location: str | None = None
    education: list[EducationDraft] = Field(default_factory=list)
    experience: list[EntryDraft] = Field(default_factory=list, description="Jobs and internships")
    projects: list[EntryDraft] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list, description="Each individual skill as its own item")
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list, description="Awards, leadership, activities")


class Bullet(BaseModel):
    id: str              # e.g. "exp0.b1" = experience entry 0, bullet 1
    text: str
    grounded: bool = True  # False = not found in the resume text -> excluded from scoring


class Entry(BaseModel):
    id: str
    title: str
    org: str | None = None
    location: str | None = None
    start: str | None = None
    end: str | None = None
    tech: list[str] = Field(default_factory=list)
    bullets: list[Bullet] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    education: list[EducationDraft] = Field(default_factory=list)
    experience: list[Entry] = Field(default_factory=list)
    projects: list[Entry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[Bullet] = Field(default_factory=list)

    def all_bullets(self) -> list[Bullet]:
        bullets = [b for entry in self.experience + self.projects for b in entry.bullets]
        return bullets + self.achievements


# ---------- General review ----------

class BulletRating(BaseModel):
    """LLM contract: one judged bullet."""
    bullet_id: str
    specificity: int = Field(ge=1, le=5)
    technical_depth: int = Field(ge=1, le=5)
    outcome: int = Field(ge=1, le=5)
    issues: list[Literal["low_depth", "unclear_outcome", "vague", "jargon"]] = Field(default_factory=list)
    rewrite: str | None = Field(None, description="Improved bullet, or null if it is already strong")
    coach_questions: list[str] = Field(default_factory=list, description="1-2 questions to the candidate")


class ReviewDraft(BaseModel):
    """LLM contract: the whole review call."""
    bullets: list[BulletRating]
    strengths: list[str] = Field(default_factory=list, description="2-3 genuine strengths of this resume")
    top_actions: list[str] = Field(default_factory=list, description="The 3 most valuable fixes, most important first")


class Finding(BaseModel):
    code: str
    message: str


class BulletFeedback(BaseModel):
    bullet_id: str
    section: Literal["experience", "projects", "achievements"]
    entry_title: str | None = None
    text: str
    issues: list[str] = Field(default_factory=list)
    specificity: int | None = None
    technical_depth: int | None = None
    outcome: int | None = None
    rewrite: str | None = None
    coach_questions: list[str] = Field(default_factory=list)
    guard_notes: list[str] = Field(default_factory=list)


class SubScore(BaseModel):
    key: str
    label: str
    score: float
    max: int
    explanation: str


class GeneralReview(BaseModel):
    overall_score: int
    sub_scores: list[SubScore]
    bullets: list[BulletFeedback]
    findings: list[Finding] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    top_actions: list[str] = Field(default_factory=list)
    ungrounded_count: int = 0


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
    profile: ResumeProfile | None = None


class FileUrl(BaseModel):
    url: str


class CreateAnalysis(BaseModel):
    resume_id: str
    mode: Literal["general", "jd"] = "general"
    jd_id: str | None = None
    target_role: str | None = Field(None, max_length=100)


class AnalysisSummary(BaseModel):
    id: str
    resume_id: str
    jd_id: str | None = None
    mode: Literal["general", "jd"]
    target_role: str | None = None
    status: Literal["queued", "running", "done", "failed"]
    error: str | None = None
    overall_score: int | None = None
    created_at: str
    completed_at: str | None = None


class AnalysisDetail(AnalysisSummary):
    sub_scores: list[SubScore] | None = None
    result: GeneralReview | None = None
    prompt_versions: dict = Field(default_factory=dict)
    model: str | None = None
