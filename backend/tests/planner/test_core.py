"""Selection, capacity, feasibility and scheduler properties (plan §4-5). No database, no LLM."""

from collections import defaultdict
from datetime import timedelta
from itertools import product

import pytest

from app.planner.builder import build_plan
from app.planner.capacity import build_calendar, final_window_days, fit
from app.planner.curriculum import load_curriculum, load_weights
from app.planner.scheduler import REVIEW_OFFSETS
from app.planner.selection import select_topics, subject_weights
from tests.planner.conftest import MONDAY, profile

# ---------- Curriculum ----------

def test_curriculum_and_weights_load_and_validate():
    curriculum = load_curriculum()
    expected = {"dsa", "os", "dbms", "cn", "oop", "lld", "hld", "projects", "aptitude", "practice", "role"}
    assert expected == set(curriculum)
    assert load_weights()["entry"]["product"]["dsa"] == 40


# ---------- Personalisation (§4) ----------

def test_subject_mix_depends_on_level_company_and_year():
    service = subject_weights(profile(company_types=["service"]))
    assert service["aptitude"] == 0.25 and "lld" not in service
    first_year = subject_weights(profile(year=1))
    assert "os" not in first_year and "cn" not in first_year and first_year["dsa"] == 0.5
    senior = subject_weights(profile(status="professional", experience_years=4, target_level="senior",
                                     year=None, goal=None))
    assert max(senior, key=senior.get) == "hld"
    mixed = subject_weights(profile(company_types=["service", "product"]))
    assert mixed["dsa"] == pytest.approx((0.25 + 0.40) / 2)


def test_level_role_track_and_language_choose_topics():
    ids = lambda p: {t.topic_id for t in select_topics(p, [], {})}  # noqa: E731
    entry, mid = ids(profile()), ids(profile(status="professional", experience_years=2, target_level="mid",
                                            year=None, goal=None))
    assert "lld.parking_lot" in entry and "lld.splitwise" not in entry and "hld.basics" not in entry
    assert {"lld.splitwise", "hld.chat"} <= mid
    assert "role.api_design" in entry and "role.react" not in entry            # backend role
    assert "project.core" in entry and "project.deepen_tests" not in entry      # build track (1 project)
    assert "project.deepen_tests" in ids(profile(projects=2, projects_deployed=True))
    beginner = [t for t in select_topics(profile(language_comfort=1, language="java"), [], {})
                if t.topic_id == "dsa.language"]
    assert beginner and beginner[0].title.startswith("Java for DSA")
    assert "dsa.language" not in entry


def test_self_rating_shrinks_topics_but_evidence_wins():
    minutes = lambda p, gaps=(), scores=None: {t.topic_id: t for t in select_topics(p, list(gaps), scores or {})}  # noqa: E731
    novice = minutes(profile(ratings={"os": 0}))["os.deadlocks"].planned_minutes
    strong = minutes(profile(ratings={"os": 4}))["os.deadlocks"].planned_minutes
    assert strong < novice / 4
    # the interview says otherwise: OS score 40 -> at least 55% of the time, and the gap raises priority
    weak = minutes(profile(ratings={"os": 4}), [("OS: Deadlocks", "interview")], {"os": 40})["os.deadlocks"]
    assert weak.planned_minutes >= round(novice * 0.55) and weak.source == "interview_gap"


def test_checkpoints_and_unmatched_gaps():
    topics = {t.topic_id: t for t in select_topics(profile(), [("Kubernetes", "jd_match")], {})}
    checkpoint = topics["os.checkpoint"]
    assert set(checkpoint.prerequisites) == {t for t in topics if t.startswith("os.") and t != "os.checkpoint"}
    assert checkpoint.details["interview"] == {"track": "fundamentals", "topics": ["os"]}
    gap = topics["gap.0"]
    assert "Kubernetes" in gap.title and gap.subject == "role"


# ---------- Capacity and feasibility (§5.1-5.2) ----------

def test_calendar_respects_weekends_rest_day_busy_dates_and_buffer():
    p = profile(rest_day="sun", busy=[{"start": "2026-12-09", "end": "2026-12-10"}])
    days = dict(build_calendar(p, MONDAY, MONDAY + timedelta(days=6), factor=0.85))
    assert days[MONDAY] == 100                                   # 2 h × 0.85 = 102 -> rounded down to 100
    assert days[MONDAY + timedelta(days=2)] == 0                 # busy
    assert days[MONDAY + timedelta(days=5)] == 255               # Saturday 5 h × 0.85
    assert days[MONDAY + timedelta(days=6)] == 0                 # rest day
    assert final_window_days(10) == 0 and final_window_days(84) == 13 and final_window_days(400) == 21


def test_fit_cuts_nice_then_should_and_never_must():
    topics = select_topics(profile(), [], {})
    kept, cut = fit(topics, capacity=60 * 60, weights=subject_weights(profile()))
    assert cut and all(t.priority != "must" for t in cut)
    priorities = [t.priority for t in cut]
    assert priorities == sorted(priorities, key=["nice", "should"].index)   # nice ones go first
    assert all(t.priority == "must" or t.source == "checkpoint" for t in kept) or len(kept) > 0


def test_short_on_time_says_so_with_a_suggestion():
    built = build_plan(profile(weekday_hours=0.5, weekend_hours=1, target_date=MONDAY + timedelta(weeks=4)),
                       MONDAY, [], {})
    assert not built.feasibility.fits and built.feasibility.cut
    assert "hours per week" in built.feasibility.suggestion


# ---------- Scheduler properties (§5.5) over many profiles ----------

PROFILES = [
    profile(**dict(zip(("weekday_hours", "weekend_hours", "company_types", "rest_day"), combo, strict=True)))
    for combo in product([0.5, 2, 4], [0, 5], [["service"], ["product"], ["top_product"]], ["none", "sun"])
    if combo[0] * 5 + combo[1] * 2 >= 1
] + [
    profile(status="professional", experience_years=2, target_level="mid", year=None, goal=None),
    profile(status="professional", experience_years=4, target_level="senior", year=None, goal=None,
            weekday_hours=1, weekend_hours=5),
    profile(year=1, weekday_hours=1, weekend_hours=2),
    profile(busy=[{"start": "2026-12-14", "end": "2026-12-20"}], target_date="2027-03-01"),
]


@pytest.mark.parametrize("p", PROFILES)
def test_scheduler_properties(p):
    built = build_plan(p, MONDAY, [], {})
    capacity = dict(build_calendar(p, MONDAY, built.target, 0.85))
    per_day = defaultdict(int)
    first_day: dict[str, object] = {}
    for task in built.schedule.tasks:
        per_day[task.date] += task.minutes
        if task.topic_id and task.kind != "review":
            first_day.setdefault(task.topic_id, task.date)

    # never over a day's usable capacity; nothing on rest days or busy dates
    assert all(minutes <= capacity[d] for d, minutes in per_day.items())
    # a topic starts only after (or on the day) its prerequisites finish
    topics = {t.topic_id: t for t in built.topics if t.status != "cut"}
    for topic_id, start in first_day.items():
        for prerequisite in topics[topic_id].prerequisites:
            if prerequisite in topics:
                assert built.schedule.finished_on[prerequisite] <= start
    # reviews come at least +2/+7/+21 days after the topic finished
    for task in built.schedule.tasks:
        if task.kind == "review":
            finished = built.schedule.finished_on[task.topic_id]
            assert task.date >= finished + timedelta(days=REVIEW_OFFSETS[task.details["stage"] - 1])
    # if the plan says every must-have fits, every must-have is scheduled
    if built.feasibility.must_covered:
        assert built.feasibility.on_track


def test_same_input_same_plan():
    first, second = build_plan(profile(), MONDAY, [], {}), build_plan(profile(), MONDAY, [], {})
    assert [(t.date, t.title, t.minutes) for t in first.schedule.tasks] == \
           [(t.date, t.title, t.minutes) for t in second.schedule.tasks]


def test_mix_follows_weights_and_long_tasks_go_to_weekends():
    built = build_plan(profile(), MONDAY, [], {})
    learning = [t for t in built.schedule.tasks if t.kind not in ("review",) and t.topic_id]
    total = sum(t.minutes for t in learning)
    dsa_share = sum(t.minutes for t in learning if t.subject == "dsa") / total
    assert abs(dsa_share - built.weights["dsa"]) < 0.12
    project_days = {t.date.weekday() for t in learning if t.subject == "projects"}
    assert project_days <= {5, 6}


def test_dsa_practice_names_problems_in_the_chosen_language():
    built = build_plan(profile(language="cpp"), MONDAY, [], {})
    practice = next(t for t in built.schedule.tasks if t.kind == "practice" and t.subject == "dsa")
    assert practice.title.endswith("in C++") and practice.details["problems"]


def test_replanning_skips_done_topics_and_schedules_their_reviews():
    p = profile()
    topics = select_topics(p, [], {})
    for topic in topics:
        if topic.topic_id == "os.processes":
            topic.status, topic.done_minutes, topic.learned_on = "done", topic.planned_minutes, MONDAY
    from app.planner.builder import schedule_topics
    from app.planner.selection import minutes_per_problem
    later = MONDAY + timedelta(days=1)
    built = schedule_topics(p, topics, subject_weights(p), later, later + timedelta(weeks=12), 0.85,
                            minutes_per_problem(p))
    learn_tasks = [t for t in built.schedule.tasks if t.topic_id == "os.processes" and t.kind != "review"]
    reviews = [t for t in built.schedule.tasks if t.topic_id == "os.processes" and t.kind == "review"]
    assert not learn_tasks
    assert reviews[0].date >= MONDAY + timedelta(days=2)
