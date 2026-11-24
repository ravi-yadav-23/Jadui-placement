"""How much time you have, and whether the selected topics fit in it (plan §5.1-5.2). Pure functions.

  daily minutes = weekday or weekend hours × 60; 0 on your rest day and busy dates
  usable        = daily minutes × capacity factor (0.85 = a 15% buffer; later your measured completion rate)
  final window  = the last ~15% of days (7-21 days) is kept for revision and mock interviews
  demand        = minutes left per topic + its three spaced reviews (topics in reviewed subjects)
  fits          = demand ≤ usable minutes before the final window, minus 5% packing slack
                  (sessions can't always fill a day to the last minute)
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from app.planner.scheduler import REVIEW_MINUTES, REVIEW_OFFSETS, REVIEWABLE
from app.planner.schemas import Feasibility, PlannerProfile, PlanTopic

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_WEEKS = {"student": {1: 24, 2: 20, 3: 16, 4: 12, 5: 12}, "graduate": 12, "professional": 12}
PRIORITY_RANK = {"nice": 0, "should": 1, "must": 2}
PACKING_SLACK = 0.95


def topic_demand(topic: PlanTopic) -> int:
    """Minutes still needed: what's left to learn, plus the reviews still to come."""
    reviews = 0
    if topic.subject in REVIEWABLE and topic.source != "checkpoint":
        reviews = (len(REVIEW_OFFSETS) - topic.review_stage) * REVIEW_MINUTES
    return max(topic.planned_minutes - topic.done_minutes, 0) + reviews


def usable_for_learning(learning_days: list[tuple[date, int]]) -> int:
    return int(sum(m for _, m in learning_days) * PACKING_SLACK)


def default_target(profile: PlannerProfile, start: date) -> date:
    weeks = DEFAULT_WEEKS[profile.status]
    if isinstance(weeks, dict):
        weeks = weeks[profile.year or 4]
    return start + timedelta(weeks=weeks)


def day_minutes(profile: PlannerProfile, day: date) -> int:
    if profile.rest_day == WEEKDAY_KEYS[day.weekday()]:
        return 0
    if any(r.start <= day <= r.end for r in profile.busy):
        return 0
    hours = profile.weekend_hours if day.weekday() >= 5 else profile.weekday_hours
    return int(hours * 60)


def build_calendar(profile: PlannerProfile, start: date, end: date, factor: float) -> list[tuple[date, int]]:
    """[(day, usable minutes)] from start to end inclusive, rounded down to 5 minutes."""
    days = (end - start).days + 1
    return [(d, int(day_minutes(profile, d) * factor) // 5 * 5) for d in (start + timedelta(i) for i in range(days))]


def final_window_days(total_days: int) -> int:
    return 0 if total_days < 14 else min(21, max(7, round(total_days * 0.15)))


def fit(topics: list[PlanTopic], capacity: int, weights: dict[str, float]) -> tuple[list[PlanTopic], list[PlanTopic]]:
    """Keep everything if it fits; otherwise cut extra-practice top-ups, then nice-to-have, then should-have topics
    (lowest-weight subject and latest topics first) until it does. Must-haves and checkpoints are never cut."""
    open_topics = [t for t in topics if t.status != "done"]
    demand = sum(topic_demand(t) for t in open_topics)
    candidates = sorted(
        (t for t in open_topics if t.priority != "must" and t.source != "checkpoint" and t.done_minutes == 0),
        key=lambda t: (not t.topic_id.endswith(".extra"), PRIORITY_RANK[t.priority], weights.get(t.subject, 0),
                       -t.position),   # extra-practice top-ups go first, then nice, then should
    )
    cut: list[PlanTopic] = []
    for topic in candidates:
        if demand <= capacity:
            break
        cut.append(topic)
        demand -= topic_demand(topic)
    cut_ids = {t.topic_id for t in cut}
    return [t for t in topics if t.topic_id not in cut_ids], cut


def feasibility(topics: list[PlanTopic], cut: list[PlanTopic], learning_days: list[tuple[date, int]],
                target: date, factor: float) -> Feasibility:
    capacity = usable_for_learning(learning_days)
    kept_demand = sum(topic_demand(t) for t in topics if t.status != "done")
    full_demand = kept_demand + sum(topic_demand(t) for t in cut)
    suggestion = None
    if full_demand > capacity:
        suggestion = _suggestion(full_demand - capacity, learning_days, target, factor)
    return Feasibility(
        fits=not cut and kept_demand <= capacity, must_covered=kept_demand <= capacity,
        demand_minutes=full_demand, capacity_minutes=capacity,
        cut=[t.title for t in cut], suggestion=suggestion,
    )


def _suggestion(shortfall: int, learning_days: list[tuple[date, int]], target: date, factor: float) -> str:
    weeks = max(len(learning_days) / 7, 1)
    extra_hours = math.ceil(shortfall / factor / weeks / 30) / 2          # rounded up to half hours
    per_day = max(sum(m for _, m in learning_days) / max(len(learning_days), 1), 1)
    later = target + timedelta(days=math.ceil(shortfall / per_day))
    return (f"To fit everything, add about {extra_hours:g} hours per week, "
            f"or move your target date to {later:%d %b %Y}.")
