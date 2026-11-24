import pytest

from app.core.config import settings
from app.resume.pipeline import scoring
from app.resume.schemas import BulletFeedback, Check, Contacts, ResumeProfile
from tests.resume import builders
from tests.resume.conftest import auth


def fb(issues: list[str], ratings=(3, 3, 3)) -> BulletFeedback:
    s, d, o = ratings
    return BulletFeedback(bullet_id="x", section="projects", text="t", issues=issues,
                          specificity=s, technical_depth=d, outcome=o)


# ---------- formulas (expected values computed by hand) ----------

def test_parse_health():
    checks = [Check(id="a", status="fail", message=""), Check(id="b", status="warn", message=""),
              Check(id="c", status="info", message=""), Check(id="d", status="pass", message="")]
    assert scoring.parse_health(checks).score == 12  # 20 - 6 - 2


def test_impact():
    bullets = [fb([]), fb(["no_metric"]), fb(["no_metric", "weak_start"]), fb(["weak_start"])]
    # 2/4 quantified -> 15 * min(1, 2/2) = 15 ; 2/4 strong starts -> 10 * 0.5 = 5
    assert scoring.impact(bullets).score == 20


def test_clarity_and_substance():
    bullets = [fb([], (5, 5, 5)), fb(["passive"], (1, 1, 1))]
    assert scoring.clarity(bullets).score == 7.5  # 1 of 2 clean
    # average rating = (15/15 + 3/15) / 2 = 0.6 -> 25 * 0.6 = 15, minus 2 * 1 unsupported skill
    assert scoring.substance(bullets, unsupported_skills=1).score == 13


def test_completeness_explains_what_is_missing():
    profile = ResumeProfile(skills=["Python"])
    sub = scoring.completeness(profile, Contacts(email="a@b.co"))
    assert sub.score == 6
    assert "Missing: education, experience or projects, LinkedIn + GitHub" in sub.explanation


def test_no_bullets_scores_zero_without_crashing():
    assert scoring.impact([]).score == 0 and scoring.substance([], 0).score == 0


# ---------- analysis API ----------

def ready_resume(client) -> str:
    resp = client.post("/api/v2/resumes", files={"file": ("Asha_Verma.pdf", builders.single_column_pdf())},
                       headers=auth())
    return resp.json()["id"]


def test_general_review_end_to_end(client):
    resume_id = ready_resume(client)
    resp = client.post("/api/v2/analyses", json={"resume_id": resume_id, "target_role": "Backend Engineer"},
                       headers=auth())
    assert resp.status_code == 202
    detail = client.get(f"/api/v2/analyses/{resp.json()['id']}", headers=auth()).json()

    assert detail["status"] == "done"
    review = detail["result"]
    assert review["overall_score"] == detail["overall_score"] == round(sum(s["score"] for s in detail["sub_scores"]))
    assert [s["key"] for s in review["sub_scores"]] == ["parse_health", "impact", "clarity", "completeness",
                                                        "substance"]
    weak = next(b for b in review["bullets"] if b["text"].startswith("Responsible for"))
    assert {"no_metric", "weak_start"} <= set(weak["issues"])
    assert weak["rewrite"].endswith("[X]%")  # placeholder, never an invented number
    assert weak["coach_questions"]
    assert any(f["code"] == "unsupported_skill" for f in review["findings"])  # Kubernetes is never shown


def test_identical_request_returns_cached_analysis(client):
    resume_id = ready_resume(client)
    first = client.post("/api/v2/analyses", json={"resume_id": resume_id}, headers=auth()).json()
    second = client.post("/api/v2/analyses", json={"resume_id": resume_id}, headers=auth())
    assert second.status_code == 200
    assert second.json()["id"] == first["id"]


def test_daily_analysis_limit(client, monkeypatch):
    resume_id = ready_resume(client)
    monkeypatch.setattr(settings, "DAILY_ANALYSIS_LIMIT", 1)
    assert client.post("/api/v2/analyses", json={"resume_id": resume_id}, headers=auth()).status_code == 202
    resp = client.post("/api/v2/analyses", json={"resume_id": resume_id, "target_role": "SDE"}, headers=auth())
    assert resp.status_code == 429


@pytest.mark.parametrize("user", ["user-b"])
def test_cannot_analyse_or_read_someone_elses_resume(client, user):
    resume_id = ready_resume(client)
    assert client.post("/api/v2/analyses", json={"resume_id": resume_id}, headers=auth(user)).status_code == 404
    analysis_id = client.post("/api/v2/analyses", json={"resume_id": resume_id}, headers=auth()).json()["id"]
    assert client.get(f"/api/v2/analyses/{analysis_id}", headers=auth(user)).status_code == 404
