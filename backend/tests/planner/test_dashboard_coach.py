"""Dashboard readiness, coach grounding + action validation, and "delete my data"."""

from datetime import timedelta

import pytest

from app.coach.schemas import CoachAction
from app.coach.service import valid_actions
from app.planner import service
from tests.planner.conftest import MONDAY, profile
from tests.resume.conftest import auth

PROFILE = profile().model_dump(mode="json")


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    clock = {"today": MONDAY}
    monkeypatch.setattr(service, "today", lambda: clock["today"])
    return clock


def test_new_user_gets_setup_steps_and_no_readiness_score(client):
    body = client.get("/api/v2/dashboard", headers=auth()).json()
    assert body["readiness"]["score"] is None                       # fewer than two parts have data
    assert [s["done"] for s in body["setup"]] == [False, False, False, False]
    assert body["next_actions"][0]["label"] == "Create your study plan"
    assert body["activity"] == []


def test_readiness_is_a_weighted_mean_of_parts_with_data(client, db):
    db.insert("interviews", "user-a", {"track": "fundamentals", "status": "completed", "score": 60,
                                       "completed_at": "2026-12-06T10:00:00",
                                       "report": {"topics": {"os": 60}, "questions": [{}], "dimensions": {}}})
    db.insert("skill_gaps", "user-a", {"skill": "OS: Deadlocks", "severity": "general", "source": "interview",
                                       "source_id": "x", "resolved_at": "2026-12-06T10:00:00"})
    db.insert("skill_gaps", "user-a", {"skill": "Docker", "severity": "must_have", "source": "jd_match",
                                       "source_id": "y"})
    body = client.get("/api/v2/dashboard", headers=auth()).json()
    parts = {p["key"]: p["value"] for p in body["readiness"]["parts"]}
    assert parts == {"resume": None, "interviews": 60, "plan": None, "gaps": 50}
    assert body["readiness"]["score"] == round((60 * 35 + 50 * 15) / 50)
    assert body["open_gaps"] == [{"skill": "Docker", "source": "jd_match"}]
    assert body["activity"][0]["title"].startswith("Mock interview (CS fundamentals): 60")


def test_plan_part_counts_done_minutes_of_the_last_two_weeks(client, _today):
    client.post("/api/v2/plans", json=PROFILE, headers=auth())
    tasks = client.get("/api/v2/plans/current/tasks", headers=auth()).json()
    monday = [t for t in tasks if t["date"] == MONDAY.isoformat()]
    for t in monday:
        client.patch(f"/api/v2/tasks/{t['id']}", json={"status": "done"}, headers=auth())
    _today["today"] = MONDAY + timedelta(days=2)       # Monday done, Tuesday missed
    body = client.get("/api/v2/dashboard", headers=auth()).json()
    plan_part = next(p for p in body["readiness"]["parts"] if p["key"] == "plan")
    assert 0 < plan_part["value"] < 100
    assert body["setup"][0]["done"] is True
    assert any(a["kind"] == "tasks" for a in body["activity"])


def test_coach_reply_is_grounded_and_invented_actions_are_dropped(client):
    client.post("/api/v2/plans", json=PROFILE, headers=auth())
    resp = client.post("/api/v2/coach/messages", json={"content": "I finished my first task, what next?"},
                       headers=auth())
    assert resp.status_code == 200
    reply = resp.json()
    first_task = client.get("/api/v2/plans/current/tasks", headers=auth()).json()[0]
    assert first_task["title"] in reply["content"]                   # grounded in the real plan
    types = [a["type"] for a in reply["actions"]]
    assert types == ["mark_task_done", "open_page"]                  # the invented task id was dropped
    assert reply["actions"][0]["task_id"] == first_task["id"]
    history = client.get("/api/v2/coach/messages", headers=auth()).json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert client.get("/api/v2/coach/messages", headers=auth("user-b")).json() == []
    assert client.delete("/api/v2/coach/messages", headers=auth()).status_code == 204
    assert client.get("/api/v2/coach/messages", headers=auth()).json() == []


def test_action_validation_rules():
    tasks = [{"id": "t1", "status": "todo"}, {"id": "t2", "status": "done"}]
    context = {"today": "2026-12-07", "plan": {"target_date": "2027-03-01", "tasks": tasks}}
    actions = [
        CoachAction(type="mark_task_done", label="Done", task_id="t1"),
        CoachAction(type="mark_task_done", label="Already done", task_id="t2"),
        CoachAction(type="move_task", label="Move", task_id="t1", date="2026-12-01"),      # in the past
        CoachAction(type="move_task", label="Move", task_id="t1", date="2026-12-09"),
        CoachAction(type="open_page", label="Open"),                                        # no page
        CoachAction(type="start_interview", label="Practise OS", track="fundamentals", topics=["os"]),
    ]
    kept = valid_actions(actions, context)
    assert [(a.type, a.label) for a in kept] == [("mark_task_done", "Done"), ("move_task", "Move"),
                                                 ("start_interview", "Practise OS")]
    assert valid_actions([CoachAction(type="replan", label="Re-plan")], {"today": "2026-12-07"}) == []


def test_delete_my_data_removes_everything(client, db):
    client.post("/api/v2/plans", json=PROFILE, headers=auth())
    client.post("/api/v2/coach/messages", json={"content": "hi"}, headers=auth())
    client.post("/api/v2/plans", json=PROFILE, headers=auth("user-b"))
    assert client.delete("/api/v2/me/data", headers=auth()).status_code == 204
    for table in ("plans", "plan_tasks", "plan_topics", "planner_profiles", "coach_messages"):
        assert db.list(table, "user-a") == []
    assert db.list("plans", "user-b")                                 # other users untouched
