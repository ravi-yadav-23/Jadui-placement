"""Every data shape used by the planner: the questionnaire, plan pieces, LLM contracts and API models."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Level = Literal["entry", "mid", "senior"]
CompanyType = Literal["service", "product", "top_product"]
RatingKey = Literal["dsa", "os", "dbms", "cn", "oop", "system_design", "aptitude"]
Weekday = Literal["none", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]


# ---------- Questionnaire ----------

class BusyRange(BaseModel):
    start: date
    end: date
    label: str | None = Field(None, max_length=60)

    @model_validator(mode="after")
    def _ordered(self):
        if self.end < self.start:
            raise ValueError("A busy range must end on or after its start date")
        return self


class PlannerProfile(BaseModel):
    """The answers to the five-step questionnaire. Conditional fields are checked in `_conditional`."""
    # Step 1: about you
    status: Literal["student", "graduate", "professional"]
    degree: Literal["btech", "bca", "mca", "mtech", "bsc", "other"] | None = None
    year: int | None = Field(None, ge=1, le=5)                  # students only
    graduation: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")  # "2028-06"
    goal: Literal["internship", "placement"] | None = None      # students only
    experience_years: float | None = Field(None, ge=0, le=15)   # professionals only
    current_role: str | None = Field(None, max_length=80)
    stack: list[str] = Field(default_factory=list, max_length=20)
    # Step 2: target
    target_role: Literal["sde", "backend", "frontend", "fullstack", "data"] = "sde"
    target_level: Level = "entry"                                # used for professionals only
    company_types: list[CompanyType] = Field(min_length=1)
    target_date: date | None = None
    # Step 3: time
    weekday_hours: float = Field(ge=0, le=8)
    weekend_hours: float = Field(ge=0, le=10)
    rest_day: Weekday = "none"
    busy: list[BusyRange] = Field(default_factory=list, max_length=20)
    study_time: Literal["morning", "afternoon", "evening", "night"] = "evening"
    # Step 4: skills
    language: Literal["cpp", "java", "python", "javascript", "go"] = "python"
    language_comfort: int = Field(2, ge=1, le=4)
    ratings: dict[RatingKey, int] = Field(default_factory=dict)  # 0 never studied ... 4 strong
    problems_solved: Literal["0", "lt50", "50_150", "150_300", "300_plus"] = "0"
    projects: int = Field(0, ge=0, le=3)                         # 3 means "3 or more"
    projects_deployed: bool = False
    # Step 5: what we already know
    include_gaps: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _conditional(self):
        if self.status == "student" and (self.year is None or self.goal is None):
            raise ValueError("Students: tell us your year of study and whether you want an internship or placement")
        if self.status == "professional" and self.experience_years is None:
            raise ValueError("Professionals: tell us your years of experience")
        if self.weekday_hours * 5 + self.weekend_hours * 2 < 1:
            raise ValueError("Plan at least one hour per week")
        if any(not 0 <= v <= 4 for v in self.ratings.values()):
            raise ValueError("Ratings go from 0 (never studied) to 4 (strong)")
        return self

    @property
    def level(self) -> Level:
        """Students and graduates prepare for entry-level roles; professionals choose."""
        return self.target_level if self.status == "professional" else "entry"


class ProfileSuggestions(BaseModel):
    """Pre-filled from the other pillars, for the user to confirm."""
    resume_title: str | None = None
    projects: int | None = None
    stack: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    interview_topics: dict[str, int] = Field(default_factory=dict)   # e.g. {"os": 45}
    ratings: dict[str, int] = Field(default_factory=dict)            # suggested from interview scores


class ProfileResponse(BaseModel):
    profile: PlannerProfile | None
    suggestions: ProfileSuggestions


# ---------- Plan pieces ----------

class PlanTopic(BaseModel):
    """One topic in a plan, with its progress. Stored as a plan_topics row."""
    topic_id: str
    subject: str
    title: str
    priority: Literal["must", "should", "nice"]
    source: Literal["curriculum", "resume_gap", "interview_gap", "checkpoint"] = "curriculum"
    position: int
    planned_minutes: int
    learn_minutes: int = 0
    prerequisites: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)
    done_minutes: int = 0
    status: Literal["planned", "in_progress", "done", "cut"] = "planned"
    learned_on: date | None = None
    review_stage: int = 0


class SubjectAllocation(BaseModel):
    subject: str
    label: str
    weight: int                    # % of study time
    planned_minutes: int
    done_minutes: int = 0


class Feasibility(BaseModel):
    fits: bool                     # everything selected fits in the time you have
    must_covered: bool             # at least every must-have topic fits
    demand_minutes: int
    capacity_minutes: int
    cut: list[str] = Field(default_factory=list)       # titles of topics left out
    suggestion: str | None = None
    on_track: bool = True          # updated as the plan rolls forward


class Phase(BaseModel):
    name: str
    start: date
    end: date


class WeekMilestone(BaseModel):
    week_start: date
    phase: str
    minutes: int
    subjects: dict[str, int]       # minutes per subject that week
    finishes: list[str]            # topics completed that week


class Roadmap(BaseModel):
    phases: list[Phase]
    weeks: list[WeekMilestone]


class PhaseText(BaseModel):
    name: str
    text: str


class RoadmapSummary(BaseModel):
    overview: str
    phases: list[PhaseText] = Field(default_factory=list)
    source: Literal["ai", "template"] = "template"


class ProjectIdea(BaseModel):
    title: str = Field(description="Short project name")
    why: str = Field(description="One sentence: why this project fits the target role")
    tech: list[str] = Field(description="3-6 technologies")
    milestones: list[str] = Field(description="4-6 milestones, each a short action")


class SummaryDraft(BaseModel):
    """LLM contract for planner_summary.v1."""
    overview: str
    phases: list[PhaseText]


class ProjectsDraft(BaseModel):
    """LLM contract for planner_projects.v1."""
    projects: list[ProjectIdea]


# ---------- API ----------

class PlanPreview(BaseModel):
    start_date: date
    target_date: date
    weeks: float
    hours_per_week: float          # usable hours (after the buffer)
    allocation: list[SubjectAllocation]
    feasibility: Feasibility
    roadmap: Roadmap


class TopicOut(BaseModel):
    topic_id: str
    subject: str
    title: str
    priority: str
    source: str
    planned_minutes: int
    done_minutes: int
    status: str


class PlanDetail(PlanPreview):
    id: str
    status: Literal["active", "archived"]
    created_at: str
    capacity_factor: float
    summary: RoadmapSummary | None = None
    projects: list[ProjectIdea] | None = None
    topics: list[TopicOut]
    study_time: str
    checkin_due: bool = False


class TaskOut(BaseModel):
    id: str
    date: date
    position: int
    kind: Literal["learn", "practice", "review", "project", "mock", "checkpoint"]
    subject: str
    topic_id: str | None = None
    title: str
    minutes: int
    details: dict = Field(default_factory=dict)
    status: Literal["todo", "done", "skipped"]


class TaskUpdate(BaseModel):
    status: Literal["todo", "done", "skipped"]


class TaskMove(BaseModel):
    date: date


class CheckinRequest(BaseModel):
    difficulty: Literal["too_easy", "right", "too_hard"]
    note: str | None = Field(None, max_length=500)
    busy: list[BusyRange] = Field(default_factory=list, max_length=10)


class PlannerOverview(BaseModel):
    """Compact summary for the dashboard and coach chat."""
    has_plan: bool
    target_date: date | None = None
    today: list[TaskOut] = Field(default_factory=list)
    week_planned_minutes: int = 0
    week_done_minutes: int = 0
    streak_days: int = 0
    on_track: bool | None = None
    next_milestone: str | None = None
