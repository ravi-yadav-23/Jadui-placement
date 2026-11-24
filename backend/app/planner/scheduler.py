"""The scheduler: turns topics + subject weights + your calendar into dated tasks (plan §5). Pure and deterministic.

For each day, in order:
  1. Spaced reviews that are due (+2, +7, +21 days after finishing a topic), 15 min each, at most 20% of the day.
  2. Learning sessions until the day is full. The next subject is the one furthest BEHIND its share
     ("deficit" = weight × minutes scheduled so far − minutes this subject got), so subjects interleave
     and the mix matches the weights. A topic only starts once its prerequisites are finished.
     Weekdays get short sessions; long subjects (projects, LLD, HLD) wait for weekends when possible.
  3. In the final window (last ~15% of days): revision and mock interviews from FINAL_TASKS.

Same input -> same output, so plans are testable and explainable. Nothing here calls an LLM.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.planner.schemas import Phase, PlanTopic, Roadmap, WeekMilestone

REVIEW_OFFSETS = (2, 7, 21)
REVIEW_MINUTES = 15
MAX_REVIEW_SHARE = 0.2
MIN_SESSION = 25
DEFAULT_SESSION = 60
LONG_SESSION = {"projects": 120, "lld": 120, "hld": 90}
LONG_SUBJECTS = set(LONG_SESSION)
REVIEWABLE = {"dsa", "os", "dbms", "cn", "oop"}
CS_SUBJECTS = ["os", "dbms", "cn", "oop"]
CS_LABELS = {"os": "OS", "dbms": "DBMS", "cn": "Computer Networks", "oop": "OOP"}


@dataclass
class TaskDraft:
    date: date
    position: int
    kind: str
    subject: str
    topic_id: str | None
    title: str
    minutes: int
    details: dict = field(default_factory=dict)


@dataclass
class Unit:
    """A topic still to be scheduled, with the minutes left."""
    topic: PlanTopic
    remaining: int
    learn_left: int
    practice_done: int = 0   # DSA practice minutes already placed (to pick the next suggested problems)
    sessions: int = 0


@dataclass
class Review:
    due: date
    topic_id: str
    subject: str
    title: str
    stage: int


@dataclass
class Schedule:
    tasks: list[TaskDraft]
    finished_on: dict[str, date]
    unscheduled: list[str]
    roadmap: Roadmap


@dataclass
class Settings:
    weights: dict[str, float]
    language: str                    # display name, e.g. "Python"
    minutes_per_problem: float
    level: str                       # entry | mid | senior
    reserved: dict[date, int] = field(default_factory=dict)   # minutes already taken by pinned tasks


def build_schedule(topics: list[PlanTopic], calendar: list[tuple[date, int]], final_days: int,
                   settings: Settings) -> Schedule:
    in_plan = {t.topic_id for t in topics if t.status != "cut"}
    finished: dict[str, date] = {}
    reviews: list[Review] = []
    queues: dict[str, list[Unit]] = defaultdict(list)
    for topic in sorted(topics, key=lambda t: (t.subject, t.position)):
        remaining = topic.planned_minutes - topic.done_minutes
        if topic.status == "cut":
            continue
        if topic.status == "done" or remaining <= 0:
            finished[topic.topic_id] = topic.learned_on or date.min   # done before this plan
            reviews += _pending_reviews(topic)
            continue
        queues[topic.subject].append(Unit(topic, remaining, max(topic.learn_minutes - topic.done_minutes, 0)))

    allocated: dict[str, int] = defaultdict(int)
    tasks: list[TaskDraft] = []
    final_start = calendar[-final_days][0] if final_days else None
    final_counter = 0
    learning_end: date | None = None

    for day, capacity in calendar:
        capacity -= settings.reserved.get(day, 0)
        day_tasks: list[TaskDraft] = []
        remaining = capacity - _place_reviews(day, capacity, reviews, day_tasks)
        tried: set[str] = set()
        while remaining >= MIN_SESSION:
            subject = _pick_subject(queues, day, finished, in_plan, allocated, settings.weights, tried)
            if subject is None:
                break
            unit = queues[subject][0]
            session = _next_session(unit, remaining, settings)
            if session is None:
                tried.add(subject)
                continue
            day_tasks.append(TaskDraft(day, 0, *session))
            learning_end = day
            minutes = session[4]
            unit.remaining -= minutes
            unit.sessions += 1
            allocated[subject] += minutes
            remaining -= minutes
            if unit.remaining <= 0:
                queues[subject].pop(0)
                finished[unit.topic.topic_id] = day
                if subject in REVIEWABLE:
                    reviews += [Review(day + timedelta(days=off), unit.topic.topic_id, subject, unit.topic.title, i + 1)
                                for i, off in enumerate(REVIEW_OFFSETS)]
        all_learned = not any(queues.values())
        if (final_start and day >= final_start) or (all_learned and day != learning_end):
            final_counter = _fill_final_day(day, remaining, settings, final_counter, day_tasks)
        for position, task in enumerate(day_tasks):
            task.position = position
        tasks += day_tasks

    unscheduled = [u.topic.topic_id for q in queues.values() for u in q]
    return Schedule(tasks, finished, unscheduled, _roadmap(calendar, final_days, learning_end, tasks, finished, topics))


# ---------- Reviews ----------

def _pending_reviews(topic: PlanTopic) -> list[Review]:
    if topic.subject not in REVIEWABLE or not topic.learned_on:
        return []
    return [Review(topic.learned_on + timedelta(days=REVIEW_OFFSETS[stage]), topic.topic_id, topic.subject,
                   topic.title, stage + 1) for stage in range(topic.review_stage, len(REVIEW_OFFSETS))]


def _place_reviews(day: date, capacity: int, reviews: list[Review], out: list[TaskDraft]) -> int:
    """Due reviews first, oldest first, within 20% of the day. Ones that don't fit wait for the next day."""
    budget = int(capacity * MAX_REVIEW_SHARE)
    used = 0
    for review in sorted((r for r in reviews if r.due <= day), key=lambda r: r.due):
        if used + REVIEW_MINUTES > budget:
            break
        out.append(TaskDraft(day, 0, "review", review.subject, review.topic_id, f"Review: {review.title}",
                             REVIEW_MINUTES, {"stage": review.stage,
                                              "how": "Explain it out loud in two minutes, then check your notes "
                                                     "or redo one problem without looking."}))
        reviews.remove(review)
        used += REVIEW_MINUTES
    return used


# ---------- Learning sessions ----------

def _pick_subject(queues, day, finished, in_plan, allocated, weights, tried) -> str | None:
    def ready(unit: Unit) -> bool:   # prerequisites outside the plan (cut / not selected) don't block
        return all(p in finished or p not in in_plan for p in unit.topic.prerequisites)

    candidates = [s for s, q in queues.items() if q and s not in tried and ready(q[0])]
    weekend = day.weekday() >= 5
    if not weekend and any(s not in LONG_SUBJECTS for s in candidates):
        candidates = [s for s in candidates if s not in LONG_SUBJECTS]
    if not candidates:
        return None
    total = sum(allocated.values()) + 1

    def deficit(subject: str) -> float:
        weight = weights.get(subject, 0.05) * (2 if weekend and subject in LONG_SUBJECTS else 1)
        return weight * total - allocated[subject]

    return max(candidates, key=lambda s: (deficit(s), -list(weights).index(s) if s in weights else -99))


def _next_session(unit: Unit, room: int, settings: Settings):
    """(kind, subject, topic_id, title, minutes, details) for the unit's next session, or None if it doesn't fit."""
    topic = unit.topic
    details = dict(topic.details)
    if topic.source == "checkpoint":
        if room < unit.remaining:
            return None
        return ("checkpoint", topic.subject, topic.topic_id, topic.title, unit.remaining, details)

    if topic.subject == "dsa" and unit.learn_left > 0:
        size = min(unit.learn_left, DEFAULT_SESSION, room)
        if size < min(MIN_SESSION, unit.learn_left):
            return None
        unit.learn_left -= size
        return ("learn", "dsa", topic.topic_id, f"Learn: {topic.title}", size, details)

    size = min(unit.remaining, LONG_SESSION.get(topic.subject, DEFAULT_SESSION), room)
    if size < _min(unit):
        return None
    if topic.subject == "dsa":
        problems = max(1, round(size / settings.minutes_per_problem))
        start = round(unit.practice_done / settings.minutes_per_problem)
        unit.practice_done += size
        details["problems"] = (topic.details.get("suggested") or [])[start:start + problems]
        noun = "problem" if problems == 1 else "problems"
        return ("practice", "dsa", topic.topic_id, f"{topic.title}: solve {problems} {noun} in {settings.language}",
                size, details)
    kind = {"projects": "project", "lld": "practice", "aptitude": "practice"}.get(topic.subject, "learn")
    if topic.details.get("interview"):
        kind = "mock"
    part = f" (part {unit.sessions + 1})" if topic.planned_minutes > LONG_SESSION.get(topic.subject, DEFAULT_SESSION) \
        else ""
    return (kind, topic.subject, topic.topic_id, topic.title + part, size, details)


def _min(unit: Unit) -> int:
    """Small leftovers of a topic may be shorter than MIN_SESSION; new sessions may not."""
    return min(MIN_SESSION, unit.remaining)


# ---------- Final window ----------

def _final_tasks(settings: Settings) -> list[tuple]:
    cs = [s for s in CS_SUBJECTS if s in settings.weights]
    tasks = [("practice", "dsa", f"Timed DSA: two problems from topics you finished, in {settings.language}", 60, {})]
    if settings.level == "entry":
        tasks.append(("mock", "practice", "Mock interview: mixed campus round", 45, {"interview": {"track": "mixed"}}))
    else:
        tasks.append(("mock", "hld", "System design drill: one question, 45 minutes, then compare with a reference",
                      60, {}))
    tasks += [("learn", s, f"Revise {CS_LABELS[s]}: explain five topics out loud without notes", 30,
               {"interview": {"track": "fundamentals", "topics": [s]}}) for s in cs]
    return tasks


def _fill_final_day(day: date, room: int, settings: Settings, counter: int, out: list[TaskDraft]) -> int:
    templates = _final_tasks(settings)
    for _ in range(len(templates)):
        if room < MIN_SESSION:
            break
        kind, subject, title, minutes, details = templates[counter % len(templates)]
        size = min(minutes, room)
        out.append(TaskDraft(day, 0, kind, subject, None, title, size, dict(details)))
        room -= size
        counter += 1
    return counter


# ---------- Roadmap (phases + weekly milestones) ----------

def _roadmap(calendar, final_days, learning_end, tasks, finished, topics) -> Roadmap:
    """Phases follow the real schedule: learning ends where the last learning session is (or where the
    final window starts, whichever is first); everything after it is revision and mocks."""
    days = [d for d, _ in calendar]
    final_start = days[-final_days] if final_days else days[-1] + timedelta(days=1)
    if learning_end and learning_end < final_start:
        final_start = learning_end + timedelta(days=1)
    learning = [d for d in days if d < final_start]
    revision = [d for d in days if d >= final_start]
    phases = []
    if learning:
        cut1, cut2 = round(len(learning) * 0.25), round(len(learning) * 0.75)
        for name, chunk in (("Foundation", learning[:cut1]), ("Core", learning[cut1:cut2]),
                            ("Advanced", learning[cut2:])):
            if chunk:
                phases.append(Phase(name=name, start=chunk[0], end=chunk[-1]))
    if revision:
        phases.append(Phase(name="Final revision and mocks", start=revision[0], end=revision[-1]))

    titles = {t.topic_id: t.title for t in topics}
    weeks: dict[date, WeekMilestone] = {}
    for d in days:
        monday = d - timedelta(days=d.weekday())
        if monday not in weeks:
            phase = next((p.name for p in phases if p.start <= d <= p.end), phases[0].name if phases else "")
            weeks[monday] = WeekMilestone(week_start=monday, phase=phase, minutes=0, subjects={}, finishes=[])
    for task in tasks:
        week = weeks[task.date - timedelta(days=task.date.weekday())]
        week.minutes += task.minutes
        week.subjects[task.subject] = week.subjects.get(task.subject, 0) + task.minutes
    for topic_id, d in finished.items():
        monday = d - timedelta(days=d.weekday())
        if monday in weeks and topic_id in titles and d >= days[0]:
            weeks[monday].finishes.append(titles[topic_id])
    return Roadmap(phases=phases, weeks=list(weeks.values()))
