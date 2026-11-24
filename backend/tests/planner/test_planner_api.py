"""Planner flows through the HTTP API (memory DB + fake LLM). `today` is pinned so dates are predictable."""

from datetime import timedelta

import pytest

from app.planner import service
from tests.planner.conftest import MONDAY, profile
from tests.resume.conftest import auth

PROFILE = profile().model_dump(mode="json")


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    clock = {"today": MONDAY}
    monkeypatch.setattr(service, "today", lambda: clock["today"])
    return clock


def create(client, body=None, user="user-a"):
    resp = client.post("/api/v2/plans", json=body or PROFILE, headers=auth(user))
    assert resp.status_code == 201, resp.json()
    return resp.json()


def tasks(client, user="user-a", **params):
    return client.get("/api/v2/plans/current/tasks", params=params, headers=auth(user)).json()


def test_questionnaire_rules():
    bad = {**PROFILE, "year": None}
    assert "year of study" in str(pytest.raises(ValueError, profile, year=None).value)
    assert bad["status"] == "student"
    with pytest.raises(ValueError):
        profile(status="professional", experience_years=None, year=None, goal=None)
    assert profile(status="graduate", year=None, goal=None, target_level="senior").level == "entry"


def test_preview_does_not_save(client, db):
    resp = client.post("/api/v2/plans/preview", json=PROFILE, headers=auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["feasibility"]["capacity_minutes"] > 0 and body["roadmap"]["phases"]
    assert db.list("plans", "user-a") == []


def test_create_plan_stores_topics_and_two_weeks_of_tasks(client, db):
    plan = create(client)
    assert plan["status"] == "active" and plan["weeks"] > 10
    assert {a["subject"] for a in plan["allocation"]} >= {"dsa", "os", "projects"}
    assert plan["summary"]["source"] == "template"      # AI text is written in the background, after this response
    rows = tasks(client)
    dates = {r["date"] for r in rows}
    assert min(dates) == MONDAY.isoformat() and max(dates) < (MONDAY + timedelta(days=14)).isoformat()
    assert db.find_one("planner_profiles", "user-a")["answers"]["year"] == 3
    detail = client.get("/api/v2/plans/current", headers=auth()).json()
    assert detail["summary"]["source"] == "ai" and detail["projects"][0]["title"]


def test_new_plan_archives_the_old_one(client, db):
    first = create(client)
    second = create(client, {**PROFILE, "weekday_hours": 3})
    assert db.get("plans", "user-a", first["id"])["status"] == "archived"
    assert client.get("/api/v2/plans/current", headers=auth()).json()["id"] == second["id"]


def test_done_task_counts_toward_topic_and_finishing_schedules_reviews(client, db, _today):
    create(client)
    learn = next(t for t in tasks(client) if t["topic_id"] == "dsa.complexity" and t["kind"] == "learn")
    topic_tasks = [t for t in tasks(client) if t["topic_id"] == "dsa.complexity" and t["kind"] != "review"]
    for t in topic_tasks:
        assert client.patch(f"/api/v2/tasks/{t['id']}", json={"status": "done"}, headers=auth()).status_code == 200
    topic = db.find_one("plan_topics", "user-a", topic_id="dsa.complexity")
    assert topic["status"] == "done" and topic["learned_on"] == MONDAY.isoformat()
    # undo one: the topic is no longer done
    client.patch(f"/api/v2/tasks/{learn['id']}", json={"status": "todo"}, headers=auth())
    assert db.find_one("plan_topics", "user-a", topic_id="dsa.complexity")["status"] == "in_progress"
    client.patch(f"/api/v2/tasks/{learn['id']}", json={"status": "done"}, headers=auth())

    _today["today"] = MONDAY + timedelta(days=3)       # come back on Thursday: missed tasks re-planned
    client.get("/api/v2/plans/current", headers=auth())
    rows = tasks(client)
    past = [t for t in rows if t["date"] < _today["today"].isoformat()]
    assert all(t["status"] != "todo" for t in past)                       # missed tasks are marked, not lost
    assert any(t["details"].get("missed") for t in past)
    assert not [t for t in rows if t["topic_id"] == "dsa.complexity" and t["kind"] in ("learn", "practice")
                and t["status"] == "todo"]
    reviews = [t for t in rows if t["topic_id"] == "dsa.complexity" and t["kind"] == "review"]
    assert reviews and reviews[0]["date"] >= (MONDAY + timedelta(days=2)).isoformat()


def test_move_pins_a_task_and_replan_keeps_it(client):
    create(client)
    task = min((t for t in tasks(client) if t["kind"] != "review"), key=lambda t: t["minutes"])
    saturday = (MONDAY + timedelta(days=5)).isoformat()
    moved = client.post(f"/api/v2/tasks/{task['id']}/move", json={"date": saturday}, headers=auth())
    assert moved.status_code == 200 and moved.json()["details"]["pinned"]
    client.post("/api/v2/plans/current/replan", headers=auth())
    assert any(t["id"] == task["id"] and t["date"] == saturday for t in tasks(client))
    yesterday = (MONDAY - timedelta(days=1)).isoformat()
    assert client.post(f"/api/v2/tasks/{task['id']}/move", json={"date": yesterday}, headers=auth()).status_code == 422


def test_checkin_lowers_capacity_from_real_completion(client, db, _today):
    create(client)
    for week in (1, 2, 3):   # the first check-in covers the week before the plan started (nothing planned)
        _today["today"] = MONDAY + timedelta(weeks=week)
        client.get("/api/v2/plans/current", headers=auth())
        resp = client.post("/api/v2/plans/current/checkins", json={"difficulty": "too_hard"}, headers=auth())
        assert resp.status_code == 200
    plan = db.find_one("plans", "user-a", status="active")
    assert plan["capacity_factor"] == 0.4                 # nothing was done -> the floor
    assert plan["settings"]["minutes_per_problem"] > 35   # "too hard" twice -> more time per problem


def test_weak_mock_interview_adds_a_relearn_topic(client, db, _today):
    plan = create(client)
    db.insert("interviews", "user-a", {"status": "completed", "completed_at": "2999-01-01T00:00:00",
                                       "report": {"topics": {"os": 40}, "questions": [], "dimensions": {}}})
    client.post("/api/v2/plans/current/replan", headers=auth())
    relearn = db.find_one("plan_topics", "user-a", plan_id=plan["id"], topic_id="os.relearn")
    assert relearn and relearn["source"] == "interview_gap"


def test_profile_suggestions_from_other_pillars(client, db):
    db.insert("skill_gaps", "user-a", {"skill": "Docker", "severity": "must_have", "source": "jd_match",
                                       "source_id": "x"})
    db.insert("interviews", "user-a", {"status": "completed", "completed_at": "2026-12-01T00:00:00",
                                       "report": {"topics": {"dbms": 80}, "questions": [], "dimensions": {}}})
    body = client.get("/api/v2/planner/profile", headers=auth()).json()
    assert body["profile"] is None
    assert body["suggestions"]["gaps"] == ["Docker"]
    assert body["suggestions"]["ratings"] == {"dbms": 3}
    gap_plan = create(client, {**PROFILE, "include_gaps": ["Docker"]})
    topic_ids = {t["topic_id"] for t in gap_plan["topics"]}
    assert "role.docker" in topic_ids
    assert next(t for t in gap_plan["topics"] if t["topic_id"] == "role.docker")["source"] == "resume_gap"


def test_summary_and_ownership(client):
    assert client.get("/api/v2/planner/summary", headers=auth()).json() == {
        "has_plan": False, "target_date": None, "today": [], "week_planned_minutes": 0, "week_done_minutes": 0,
        "streak_days": 0, "on_track": None, "next_milestone": None}
    create(client)
    first = tasks(client)[0]
    client.patch(f"/api/v2/tasks/{first['id']}", json={"status": "done"}, headers=auth())
    summary = client.get("/api/v2/planner/summary", headers=auth()).json()
    assert summary["has_plan"] and summary["streak_days"] == 1 and summary["today"]
    assert summary["week_done_minutes"] == first["minutes"]
    assert client.get("/api/v2/plans/current", headers=auth("user-b")).status_code == 404
    other = client.patch(f"/api/v2/tasks/{first['id']}", json={"status": "todo"}, headers=auth("user-b"))
    assert other.status_code == 404


def test_target_date_must_be_reasonable(client):
    resp = client.post("/api/v2/plans/preview", json={**PROFILE, "target_date": MONDAY.isoformat()}, headers=auth())
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "bad_target_date"
