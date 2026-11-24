"""Full interview flows through the HTTP API (memory DB + fake LLM).
TestClient runs background tasks before returning, so each answer is already judged on return."""

from app.core.config import settings
from tests.resume import builders
from tests.resume.conftest import auth

GOOD = ("A deadlock is when processes wait on each other forever. The four Coffman conditions are mutual "
        "exclusion, hold and wait, no preemption and circular wait. Prevention breaks one condition, for "
        "example lock ordering. Avoidance uses the Banker's algorithm; detection and recovery is the other option.")


def start(client, user="user-a", **body):
    payload = {"track": "fundamentals", "topics": ["os"], "question_count": 3, **body}
    return client.post("/api/v2/interviews", json=payload, headers=auth(user))


def current(detail):
    return detail["turns"][-1]


def answer(client, detail, text, user="user-a", **extra):
    turn = current(detail)
    resp = client.post(f"/api/v2/interviews/{detail['id']}/turns/{turn['id']}/answer",
                       json={"answer": text, **extra}, headers=auth(user))
    assert resp.status_code == 202, resp.json()
    return client.get(f"/api/v2/interviews/{detail['id']}", headers=auth(user)).json()


def test_fundamentals_interview_runs_to_a_report(client, db):
    resp = start(client)
    assert resp.status_code == 201                      # bank track: no planning step
    detail = resp.json()
    assert detail["status"] == "active" and detail["question_count"] == 3
    assert len(detail["turns"]) == 1 and current(detail)["status"] == "asked"

    detail = answer(client, detail, "Not sure, something about waiting.")   # weak -> follow-up
    assert current(detail)["kind"] == "follow_up"
    detail = answer(client, detail, "Still not sure.")                      # follow-up -> next question
    assert current(detail)["kind"] == "main" and detail["question_number"] == 2
    while detail["status"] == "active":
        detail = answer(client, detail, GOOD)

    assert detail["status"] == "completed"
    report = detail["report"]
    assert report["questions"] and 0 <= report["score"] <= 100
    assert all(t["evaluation"] for t in detail["turns"])       # feedback visible once completed
    gaps = db.list("skill_gaps", "user-a", source="interview")
    assert gaps and all(g["source_id"] == detail["id"] for g in gaps)


def test_answer_key_and_upcoming_questions_never_reach_the_browser(client):
    detail = start(client).json()
    assert "plan" not in detail and "settings" not in detail
    raw = client.get(f"/api/v2/interviews/{detail['id']}", headers=auth()).text
    assert "key_points" not in raw


def test_interview_mode_hides_scores_until_the_end_practice_mode_shows_them(client):
    hidden = answer(client, start(client).json(), GOOD)
    assert hidden["turns"][0]["status"] == "evaluated"
    assert hidden["turns"][0]["evaluation"] is None and hidden["turns"][0]["score"] is None

    shown = answer(client, start(client, mode="practice").json(), GOOD)
    assert shown["turns"][0]["evaluation"]["feedback"]   # feedback right after each answer
    assert shown["turns"][0]["score"] is not None


def test_only_the_current_question_can_be_answered_once(client):
    detail = start(client).json()
    first_turn = current(detail)
    detail = answer(client, detail, GOOD)
    resp = client.post(f"/api/v2/interviews/{detail['id']}/turns/{first_turn['id']}/answer",
                       json={"answer": "again"}, headers=auth())
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "turn_not_current"
    resp = client.post(f"/api/v2/interviews/{detail['id']}/turns/{current(detail)['id']}/answer",
                       json={"answer": "x" * (settings.INTERVIEW_MAX_ANSWER_CHARS + 1)}, headers=auth())
    assert resp.status_code == 422


def test_skip_and_finish_early(client):
    detail = start(client).json()
    detail = client.post(f"/api/v2/interviews/{detail['id']}/skip", headers=auth()).json()
    assert detail["turns"][0]["status"] == "skipped" and detail["question_number"] == 2
    detail = client.post(f"/api/v2/interviews/{detail['id']}/finish", headers=auth()).json()
    assert detail["status"] == "completed"
    assert len(detail["turns"]) == 1                     # the open, unanswered question was dropped
    assert detail["report"]["questions"][0]["skipped"] and detail["report"]["score"] == 0


def test_other_users_cannot_see_or_answer(client):
    detail = start(client).json()
    assert client.get(f"/api/v2/interviews/{detail['id']}", headers=auth("user-b")).status_code == 404
    resp = client.post(f"/api/v2/interviews/{detail['id']}/turns/{current(detail)['id']}/answer",
                       json={"answer": GOOD}, headers=auth("user-b"))
    assert resp.status_code == 404


def test_daily_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "DAILY_INTERVIEW_LIMIT", 1)
    assert start(client).status_code == 201
    resp = start(client)
    assert resp.status_code == 429 and resp.json()["error"]["code"] == "rate_limited"


def test_delete_removes_turns_and_gaps(client, db):
    detail = start(client).json()
    client.post(f"/api/v2/interviews/{detail['id']}/skip", headers=auth())
    client.post(f"/api/v2/interviews/{detail['id']}/finish", headers=auth())
    assert db.list("skill_gaps", "user-a", source="interview")
    assert client.delete(f"/api/v2/interviews/{detail['id']}", headers=auth()).status_code == 204
    assert db.list("interview_turns", "user-a") == [] and db.list("skill_gaps", "user-a") == []
    assert client.get(f"/api/v2/interviews/{detail['id']}", headers=auth()).status_code == 404


def ready_resume(client) -> str:
    resp = client.post("/api/v2/resumes", files={"file": ("cv.pdf", builders.single_column_pdf())}, headers=auth())
    return resp.json()["id"]


def test_resume_track_needs_a_resume_and_asks_about_its_entries(client, db):
    assert start(client, track="resume").json()["error"]["code"] == "resume_required"
    resume_id = ready_resume(client)
    resp = start(client, track="resume", resume_id=resume_id)
    assert resp.status_code == 202                       # planned in the background (1 LLM call)
    detail = client.get(f"/api/v2/interviews/{resp.json()['id']}", headers=auth()).json()
    assert detail["status"] == "active"
    plan = db.get("interviews", "user-a", detail["id"])["plan"]
    resume = db.get("resumes", "user-a", resume_id)["profile"]
    entry_ids = {e["id"] for e in resume["projects"] + resume["experience"]}
    projects = [q for q in plan if q["type"] == "project"]
    assert projects and all(set(q["source_ids"]) <= entry_ids for q in projects)
    # fewer resume entries than questions asked for: the rest is topped up from the bank
    assert len(plan) == 3 and all(q["type"] == "fundamentals" for q in plan[len(projects):])


def test_mixed_track_is_projects_then_fundamentals_then_hr(client, db):
    resume_id = ready_resume(client)
    detail = start(client, track="mixed", resume_id=resume_id, question_count=5, topics=["os", "dbms"]).json()
    plan = db.get("interviews", "user-a", detail["id"])["plan"]
    assert [q["type"] for q in plan] == ["project", "project", "fundamentals", "fundamentals", "behavioral"]


def test_jd_track_cites_requirements(client, db):
    jd_id = client.post("/api/v2/jds", json={"raw_text": builders.SAMPLE_JD}, headers=auth()).json()["id"]
    detail = start(client, track="jd", jd_id=jd_id).json()
    plan = db.get("interviews", "user-a", detail["id"])["plan"]
    requirement_ids = {r["id"] for r in db.get("job_descriptions", "user-a", jd_id)["parsed"]["requirements"]}
    assert plan and all(q["type"] == "jd" and set(q["source_ids"]) <= requirement_ids for q in plan)


def test_summary_for_other_pillars(client):
    detail = start(client).json()
    while detail["status"] == "active":
        detail = answer(client, detail, GOOD)
    summary = client.get("/api/v2/interview/summary", headers=auth()).json()
    assert summary["completed_count"] == 1
    assert summary["recent"][0]["score"] == detail["score"]
    assert "os" in summary["topic_averages"]
