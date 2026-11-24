"""Every data shape used by the interview pillar.

Three groups:
  * the plan (what we will ask, with the answer key) - stored server-side, never sent before answering
  * LLM contracts (`...Draft`) - what the model must return; validated by LLMClient.structured()
  * API models - what the browser sees
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Track = Literal["resume", "jd", "fundamentals", "behavioral", "mixed"]
QuestionType = Literal["fundamentals", "project", "jd", "behavioral"]
Topic = Literal["os", "dbms", "cn", "oop"]
Difficulty = Literal["easy", "medium", "hard", "any"]


# ---------- Plan ----------

class PlannedQuestion(BaseModel):
    id: str                                   # "q0", "q1", ... (order in the session)
    type: QuestionType
    question: str
    key_points: list[str]                     # what a strong answer covers (the answer key)
    topic: str                                # os | dbms | cn | oop | behavioral | projects | <JD skill>
    concept: str | None = None                # short name, used for skill gaps ("Deadlocks")
    source_ids: list[str] = Field(default_factory=list)  # resume bullet/entry ids or JD requirement ids
    bank_id: str | None = None                # set when the question comes from the YAML bank


class PlanQuestionDraft(BaseModel):
    question: str = Field(description="One interview question, 1-3 sentences")
    key_points: list[str] = Field(description="3-5 points a strong answer would cover")
    source_ids: list[str] = Field(description="IDs from the input that this question is about")
    concept: str = Field(description="2-4 word name of the skill or topic being tested")


class PlanDraft(BaseModel):
    """LLM contract for interview_plan.v1."""
    questions: list[PlanQuestionDraft]


# ---------- Judging ----------

class KeyPointJudgment(BaseModel):
    index: int = Field(description="Index of the key point in the list (0-based)")
    covered: bool
    quote: str | None = Field(None, description="Exact words copied from the answer that cover this point")


class DimensionScore(BaseModel):
    name: str
    anchor: int = Field(ge=1, le=5)
    reason: str = Field(description="One sentence tied to the chosen anchor")


class JudgeDraft(BaseModel):
    """LLM contract for interview_judge.v1."""
    key_points: list[KeyPointJudgment]
    dimensions: list[DimensionScore]
    feedback: str = Field(description="2-3 specific sentences: what worked, what was missing")
    follow_up: str | None = Field(None, description="One follow-up question about a missed key point, or null")


class CoveredPoint(BaseModel):
    point: str
    quote: str                                # verified: it really appears in the answer


class TurnEvaluation(BaseModel):
    covered: list[CoveredPoint]
    missed: list[str]
    dimensions: list[DimensionScore]
    rubric: int                               # 0-100, from the anchors
    coverage: int                             # 0-100, verified key points / all key points
    score: int                                # 0.6 * rubric + 0.4 * coverage
    feedback: str
    follow_up: str | None = None
    demoted_quotes: int = 0                   # "covered" claims whose quote was not in the answer


class Delivery(BaseModel):
    words: int
    wpm: int | None = None                    # only when a duration is known (voice answers)
    fillers: int = 0
    repeated: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)


# ---------- Report ----------

class QuestionReport(BaseModel):
    question_id: str
    type: QuestionType
    topic: str
    question: str
    score: int
    skipped: bool = False
    covered: list[CoveredPoint] = Field(default_factory=list)
    missed: list[str] = Field(default_factory=list)


class DeliverySummary(BaseModel):
    voice_answers: int
    wpm: int | None
    fillers_per_100_words: float
    repeated: list[str]


class InterviewReport(BaseModel):
    score: int
    band: Literal["ready", "almost", "practice"]
    dimensions: dict[str, float]              # average anchor (1-5) per dimension
    topics: dict[str, int]                    # average question score per topic
    questions: list[QuestionReport]
    delivery: DeliverySummary | None = None
    gaps: list[str] = Field(default_factory=list)


# ---------- API ----------

class CreateInterview(BaseModel):
    track: Track = "mixed"
    mode: Literal["interview", "practice"] = "interview"
    question_count: int = Field(5, ge=3, le=8)
    topics: list[Topic] = Field(default_factory=lambda: ["os", "dbms", "cn", "oop"])
    difficulty: Difficulty = "any"
    resume_id: str | None = None
    jd_id: str | None = None
    target_role: str | None = Field(None, max_length=120)


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1)
    answer_mode: Literal["text", "voice"] = "text"
    duration_seconds: int | None = Field(None, ge=0, le=3600)


class TurnOut(BaseModel):
    id: str
    idx: int
    question_id: str
    kind: Literal["main", "follow_up"]
    question: str
    answer: str | None = None
    answer_mode: Literal["text", "voice"] | None = None
    status: Literal["asked", "evaluating", "evaluated", "skipped", "failed"]
    error: str | None = None
    score: int | None = None                  # hidden (None) in interview mode until the end
    evaluation: TurnEvaluation | None = None  # hidden in interview mode until the end
    delivery: Delivery | None = None


class InterviewSummary(BaseModel):
    id: str
    track: Track
    mode: Literal["interview", "practice"]
    status: Literal["planning", "active", "completed", "failed"]
    target_role: str | None = None
    score: int | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None


class InterviewDetail(InterviewSummary):
    question_count: int                       # planned main questions
    question_number: int                      # 1-based number of the current main question
    turns: list[TurnOut]
    report: InterviewReport | None = None


class RecentInterview(BaseModel):
    id: str
    track: Track
    score: int
    created_at: str


class InterviewOverview(BaseModel):
    """Compact summary for the dashboard, planner and coach chat."""
    completed_count: int
    recent: list[RecentInterview]
    average_score: int | None
    topic_averages: dict[str, int]
    weakest_dimension: str | None
    open_gaps: list[str]
