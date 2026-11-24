"""Puts the pure steps together: selection -> calendar -> feasibility -> scheduler.

    built = build_plan(profile, start=date.today(), gaps=[("Docker", "jd_match")], interview_scores={"os": 45})

Used by the API preview, plan creation, every re-plan, and the persona eval. No database, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.core.config import settings
from app.planner.capacity import (
    build_calendar,
    default_target,
    feasibility,
    final_window_days,
    fit,
    topic_demand,
    usable_for_learning,
)
from app.planner.curriculum import load_curriculum
from app.planner.scheduler import Schedule, Settings, build_schedule
from app.planner.schemas import Feasibility, PlannerProfile, PlanTopic, SubjectAllocation
from app.planner.selection import LANGUAGES, minutes_per_problem, select_topics, subject_weights

DEFAULT_FACTOR = 1 - settings.PLANNER_BUFFER  # plan with 85% of the stated hours (15% buffer)
MIN_TOP_UP = 60
# Spare time goes to more practice in subjects that can absorb it, up to each subject's share (plan §5.2).
TOP_UPS = {
    "dsa": ("Mixed DSA practice: problems from every pattern so far", {}),
    "aptitude": ("Timed aptitude practice sets", {}),
    "practice": ("Extra mock interviews", {"interview": {"track": "mixed"}}),
    "lld": ("More machine-coding problems (90 minutes each, timed)", {}),
    "hld": ("More system design questions (45 minutes each, then compare with a reference)", {}),
}


@dataclass
class BuiltPlan:
    start: date
    target: date
    topics: list[PlanTopic]            # every topic; the ones that didn't fit have status "cut"
    schedule: Schedule
    allocation: list[SubjectAllocation]
    feasibility: Feasibility
    weights: dict[str, float]
    usable_minutes: int                # whole calendar, after the buffer


def build_plan(profile: PlannerProfile, start: date, gaps: list[tuple[str, str]],
               interview_scores: dict[str, int], factor: float = DEFAULT_FACTOR) -> BuiltPlan:
    target = profile.target_date or default_target(profile, start)
    weights = subject_weights(profile)
    topics = select_topics(profile, gaps, interview_scores)
    calendar = build_calendar(profile, start, target, factor)
    final_days = final_window_days(len(calendar))
    capacity = usable_for_learning(calendar[:-final_days] if final_days else calendar)
    topics += top_ups(topics, weights, capacity)
    return schedule_topics(profile, topics, weights, start, target, factor, minutes_per_problem(profile))


def top_ups(topics: list[PlanTopic], weights: dict[str, float], capacity: int) -> list[PlanTopic]:
    """Hand out only the SPARE time (capacity - demand) as "extra practice" topics, split between practice-heavy
    subjects by how far each is below its share. Nice-to-have, so it is the first thing cut later."""
    spare = capacity - sum(topic_demand(t) for t in topics)
    below = {}
    for subject in TOP_UPS:
        if subject in weights:
            have = sum(topic_demand(t) for t in topics if t.subject == subject)
            below[subject] = max(int(weights[subject] * capacity) - have, 0)
    total_below = sum(below.values())
    if spare <= 0 or not total_below:
        return []
    out = []
    for subject, gap in below.items():
        minutes = min(gap, int(spare * gap / total_below))
        if minutes >= MIN_TOP_UP:
            title, details = TOP_UPS[subject]
            out.append(PlanTopic(
                topic_id=f"{subject}.extra", subject=subject, title=title, priority="nice", position=999,
                planned_minutes=minutes, details=details,
                prerequisites=[t.topic_id for t in topics if t.subject == subject and t.priority == "must"]))
    return out


def schedule_topics(profile: PlannerProfile, topics: list[PlanTopic], weights: dict[str, float], start: date,
                    target: date, factor: float, per_problem: float,
                    reserved: dict[date, int] | None = None) -> BuiltPlan:
    """(Re)schedule from `start`. Topics cut earlier are reconsidered: more time can bring them back."""
    topics = [t.model_copy(update={"status": "planned"}) if t.status == "cut" else t.model_copy() for t in topics]
    calendar = build_calendar(profile, start, target, factor)
    final_days = final_window_days(len(calendar))
    learning = calendar[:-final_days] if final_days else calendar
    reserved_total = sum((reserved or {}).values())
    kept, cut = fit(topics, usable_for_learning(learning) - reserved_total, weights)
    for topic in cut:
        topic.status = "cut"
    feasible = feasibility(kept, cut, learning, target, factor)

    settings = Settings(weights=weights, language=LANGUAGES[profile.language], minutes_per_problem=per_problem,
                        level=profile.level, reserved=reserved or {})
    schedule = build_schedule(topics, calendar, final_days, settings)
    must_left = [t for t in topics if t.topic_id in schedule.unscheduled and t.priority == "must"]
    feasible.on_track = not must_left
    return BuiltPlan(start, target, topics, schedule, allocation(topics, weights), feasible, weights,
                     sum(m for _, m in calendar))


def allocation(topics: list[PlanTopic], weights: dict[str, float]) -> list[SubjectAllocation]:
    labels = {s: subject.label for s, subject in load_curriculum().items()}
    out = []
    for subject, weight in weights.items():
        mine = [t for t in topics if t.subject == subject and t.status != "cut"]
        out.append(SubjectAllocation(subject=subject, label=labels[subject], weight=round(weight * 100),
                                     planned_minutes=sum(t.planned_minutes for t in mine),
                                     done_minutes=sum(t.done_minutes for t in mine)))
    return out
