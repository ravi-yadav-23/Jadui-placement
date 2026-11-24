from app.interview.delivery import delivery_metrics
from app.interview.evaluate import judge_answer, verify_and_score
from app.interview.report import build_report
from app.interview.schemas import DimensionScore, JudgeDraft, KeyPointJudgment, PlannedQuestion
from app.llm.client import get_llm

DEADLOCK = PlannedQuestion(
    id="q0", type="fundamentals", topic="os", concept="Deadlocks", bank_id="os.deadlock",
    question="What is a deadlock and how can it be prevented?",
    key_points=["Processes wait on each other forever", "Four Coffman conditions",
                "Prevention by lock ordering", "Detection and recovery"],
)
ANSWER = ("A deadlock is when two processes wait for each other forever. "
          "You can prevent it by always taking locks in the same global order.")


def draft(*judgments, dimensions=None, follow_up="What are the necessary conditions?") -> JudgeDraft:
    return JudgeDraft(
        key_points=[KeyPointJudgment(index=i, covered=c, quote=q) for i, c, q in judgments],
        dimensions=dimensions if dimensions is not None else [
            DimensionScore(name="correctness", anchor=4, reason=""),
            DimensionScore(name="depth", anchor=3, reason=""),
            DimensionScore(name="clarity", anchor=4, reason=""),
        ],
        feedback="Good start.", follow_up=follow_up,
    )


# ---------- Verification: code checks the model's claims ----------

def test_covered_points_need_a_quote_that_is_really_in_the_answer():
    result = verify_and_score(DEADLOCK, "main", ANSWER, draft(
        (0, True, "two processes wait for each other forever"),          # real quote -> covered
        (1, True, "mutual exclusion, hold and wait, no preemption"),     # invented quote -> demoted
        (2, True, "taking locks in the same global order"),
        (9, True, "out of range index"),                                 # ignored
    ))
    assert [c.point for c in result.covered] == ["Processes wait on each other forever", "Prevention by lock ordering"]
    assert result.missed == ["Four Coffman conditions", "Detection and recovery"]
    assert result.demoted_quotes == 1
    assert result.coverage == 50
    assert result.rubric == 67                  # anchors 4, 3, 4 -> (75 + 50 + 75) / 3
    assert result.score == round(0.6 * 67 + 0.4 * 50)


def test_unknown_dimensions_are_dropped_and_missing_ones_fall_back_to_coverage():
    only_unknown = [DimensionScore(name="charisma", anchor=5, reason="")]
    result = verify_and_score(DEADLOCK, "main", ANSWER, draft((0, True, "wait for each other forever"),
                                                              dimensions=only_unknown))
    assert result.dimensions == []
    assert result.rubric == result.coverage == 25


def test_follow_up_only_for_a_main_answer_with_missed_points():
    partial = draft((0, True, "wait for each other forever"))
    assert verify_and_score(DEADLOCK, "main", ANSWER, partial).follow_up == "What are the necessary conditions?"
    assert verify_and_score(DEADLOCK, "follow_up", ANSWER, partial).follow_up is None
    everything = draft(*[(i, True, "wait for each other forever") for i in range(1)])
    full = DEADLOCK.model_copy(update={"key_points": ["Processes wait on each other forever"]})
    assert verify_and_score(full, "main", ANSWER, everything).follow_up is None


def test_judge_answer_end_to_end_with_the_fake_llm():
    llm = get_llm(None, None)
    good = judge_answer(llm, DEADLOCK, "main", DEADLOCK.question,
                        "Processes wait on each other forever in a deadlock. The four Coffman conditions must all "
                        "hold. Prevention uses lock ordering. Otherwise use detection and recovery.", None)
    weak = judge_answer(llm, DEADLOCK, "main", DEADLOCK.question, "I am not sure, something about threads.", None)
    assert good.score > weak.score
    assert good.follow_up is None and weak.follow_up


# ---------- Delivery ----------

def test_delivery_metrics():
    d = delivery_metrics("Um, basically I used Redis. Basically Redis caching, you know, Redis is fast.", 30)
    assert d.words == 13
    assert d.wpm == 26
    assert d.fillers == 4             # um, basically x2, you know
    assert d.repeated == ["redis"]
    assert "Redis" in d.terms
    assert delivery_metrics("short", None).wpm is None


# ---------- Report ----------

def turn(qid, kind, status, covered=(), rubric=50, mode="text", answer="answer"):
    evaluation = {
        "covered": [{"point": p, "quote": "q"} for p in covered], "missed": [], "rubric": rubric,
        "coverage": 0, "score": 0, "feedback": "", "demoted_quotes": 0,
        "dimensions": [{"name": "depth", "anchor": 2, "reason": ""}, {"name": "clarity", "anchor": 4, "reason": ""}],
    }
    return {"question_id": qid, "kind": kind, "status": status, "answer": answer, "answer_mode": mode,
            "evaluation": evaluation if status == "evaluated" else None, "duration_seconds": 60,
            "delivery": delivery_metrics(answer, 60).model_dump()}


def test_report_combines_follow_up_coverage_and_scores_skips_as_zero():
    second = DEADLOCK.model_copy(update={"id": "q1", "concept": "Paging"})
    turns = [
        turn("q0", "main", "evaluated", covered=["Processes wait on each other forever"], rubric=50),
        turn("q0", "follow_up", "evaluated", covered=["Four Coffman conditions", "Prevention by lock ordering"],
             rubric=70),
        turn("q1", "main", "skipped"),
    ]
    report, gaps = build_report([DEADLOCK, second], turns)
    q0, q1 = report.questions
    assert len(q0.covered) == 3 and q0.missed == ["Detection and recovery"]
    assert q0.score == round(0.6 * 60 + 0.4 * 75)     # rubric mean 60, coverage 3/4
    assert (q1.score, q1.skipped) == (0, True)
    assert report.score == round(q0.score / 2)
    assert ("OS: Paging", "general") in gaps            # skipped fundamentals question -> gap
    assert report.dimensions == {"Depth": 2.0, "Clarity": 4.0}
    assert "Explaining how things work" in report.gaps  # depth averaged <= 2
    assert report.delivery is None                      # no voice answers


def test_unanswered_and_failed_questions_are_left_out():
    second = DEADLOCK.model_copy(update={"id": "q1"})
    report, _ = build_report([DEADLOCK, second], [turn("q0", "main", "failed")])
    assert report.questions == [] and report.score == 0
