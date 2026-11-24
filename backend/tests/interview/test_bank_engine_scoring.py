from collections import Counter

import pytest

from app.interview.bank import load_bank, pick_questions
from app.interview.engine import next_step, question_number
from app.interview.rubric import anchors_text, dimensions_for, load_rubric
from app.interview.schemas import DimensionScore, PlannedQuestion
from app.interview.scoring import band, combine, coverage_score, rubric_score, session_score

TOPICS = ["os", "dbms", "cn", "oop"]


# ---------- Bank ----------

def test_bank_loads_and_is_balanced():
    counts = Counter(q.topic for q in load_bank())
    assert counts == {"os": 10, "dbms": 10, "cn": 10, "oop": 10, "behavioral": 12}


def test_same_seed_same_questions_and_topics_are_spread():
    first = pick_questions(TOPICS, "any", 4, exclude=set(), seed=7)
    assert [q.id for q in first] == [q.id for q in pick_questions(TOPICS, "any", 4, exclude=set(), seed=7)]
    assert {q.topic for q in first} == set(TOPICS)  # round-robin: one per topic


def test_recently_seen_questions_are_skipped_until_the_pool_runs_out():
    seen = {q.id for q in load_bank() if q.topic == "os"}
    assert seen.isdisjoint(q.id for q in pick_questions(["os", "dbms"], "any", 5, exclude=seen, seed=1))
    # only OS asked, all OS seen: repeats are allowed rather than a short session
    assert len(pick_questions(["os"], "any", 3, exclude=seen, seed=1)) == 3


def test_difficulty_filter():
    picked = pick_questions(TOPICS, "hard", 3, exclude=set(), seed=3)
    assert picked and all(q.difficulty == "hard" for q in picked)


# ---------- Rubric ----------

def test_every_dimension_has_five_anchors_and_types_have_dimensions():
    assert load_rubric()
    assert dimensions_for("fundamentals") == ["correctness", "depth", "clarity"]
    assert dimensions_for("behavioral") == ["structure", "impact", "reflection"]
    assert dimensions_for("project") == ["depth", "clarity", "ownership", "tradeoffs"]
    assert '"depth" (Depth):' in anchors_text("fundamentals")


# ---------- Engine ----------

def plan(n: int) -> list[PlannedQuestion]:
    return [PlannedQuestion(id=f"q{i}", type="fundamentals", question=f"Question {i}?", key_points=["a", "b"],
                            topic="os") for i in range(n)]


@pytest.mark.parametrize(("kind", "follow_up", "skipped", "question_id", "expected"), [
    ("main", "Why?", False, "q0", ("follow_up", "q0")),        # main answer + proposal -> follow-up
    ("follow_up", "Why?", False, "q0", ("ask", "q1")),         # never a second follow-up
    ("main", None, False, "q0", ("ask", "q1")),                # nothing to probe -> next question
    ("main", "Why?", True, "q0", ("ask", "q1")),               # skipped -> no follow-up
    ("main", None, False, "q2", ("finish", None)),             # last question -> finish
    ("follow_up", None, False, "q2", ("finish", None)),
])
def test_next_step(kind, follow_up, skipped, question_id, expected):
    step = next_step(plan(3), kind, question_id, follow_up, skipped)
    assert (step.action, step.question_id) == expected


def test_question_number():
    assert question_number(plan(3), "q1") == 2


# ---------- Scoring ----------

def dims(*anchors: int) -> list[DimensionScore]:
    return [DimensionScore(name=f"d{i}", anchor=a, reason="") for i, a in enumerate(anchors)]


def test_scoring_formulas():
    assert rubric_score(dims(1, 1, 1)) == 0
    assert rubric_score(dims(5, 5)) == 100
    assert rubric_score(dims(3, 4)) == 62  # (50 + 75) / 2 = 62.5 -> 62 (banker's rounding)
    assert coverage_score(3, 4) == 75
    assert combine(rubric=50, coverage=100) == 70  # 0.6 * 50 + 0.4 * 100
    assert session_score([80, 0, 70]) == 50
    assert session_score([]) == 0
    assert (band(75), band(74), band(55), band(54)) == ("ready", "almost", "almost", "practice")
