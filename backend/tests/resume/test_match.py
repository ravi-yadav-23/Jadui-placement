import pytest

from app.resume.pipeline import scoring
from app.resume.pipeline.knockouts import check_knockouts
from app.resume.pipeline.match import bullet_refs, listed_skills, rule_match, validate_judgment
from app.resume.schemas import KnockoutDraft, Requirement, RequirementJudgment, RequirementMatch, ResumeProfile
from tests.resume import builders
from tests.resume.builders import SAMPLE_JD
from tests.resume.conftest import auth

PROFILE = ResumeProfile.model_validate({
    "location": "Pune, India",
    "education": [{"institution": "Example Institute", "grad_year": 2026, "cgpa": 8.4, "cgpa_scale": 10}],
    "skills": ["Python", "FastAPI", "Docker", "Kubernetes"],
    "experience": [{"id": "exp0", "title": "Backend Intern", "tech": ["Redis"], "bullets": [
        {"id": "exp0.b0", "text": "Built a FastAPI service for invoice reconciliation handling 20k requests per day"},
    ]}],
})


def req(text: str, skills: list[str], kind: str = "must") -> Requirement:
    return Requirement(id="r0", text=text, kind=kind, skills=skills)


# ---------- evidence ----------

def test_rules_find_proof_including_implied_skills():
    match = rule_match(req("Strong Python", ["Python"]), bullet_refs(PROFILE))
    assert match.status == "strong" and match.decided_by == "rules"
    assert [e.bullet_id for e in match.evidence] == ["exp0.b0"]  # FastAPI bullet proves Python


def test_rules_defer_to_ai_when_any_skill_is_unproven():
    assert rule_match(req("Python and Docker", ["Python", "Docker"]), bullet_refs(PROFILE)) is None


def test_ai_evidence_must_point_at_real_bullets():
    refs = {r.bullet.id: r for r in bullet_refs(PROFILE)}
    fake = RequirementJudgment(requirement_id="r0", status="strong", evidence_bullet_ids=["exp9.b9"],
                               reason="trust me")
    assert validate_judgment(req("Kafka", ["Kafka"]), fake, refs, listed_skills(PROFILE)).status == "missing"


def test_listed_but_unproven_skill_is_listed_only():
    refs = {r.bullet.id: r for r in bullet_refs(PROFILE)}
    missing = RequirementJudgment(requirement_id="r0", status="missing", reason="no")
    result = validate_judgment(req("Docker", ["Docker"]), missing, refs, listed_skills(PROFILE))
    assert result.status == "listed_only"


# ---------- knockouts ----------

@pytest.mark.parametrize(("rule", "status"), [
    (KnockoutDraft(type="cgpa", value="Minimum CGPA 7.5"), "ok"),
    (KnockoutDraft(type="cgpa", value="CGPA 9.0 and above"), "conflict"),
    (KnockoutDraft(type="cgpa", value="70% throughout"), "ok"),       # 70% ~ 7.37 CGPA
    (KnockoutDraft(type="grad_year", value="2026 batch only"), "ok"),
    (KnockoutDraft(type="grad_year", value="2024/2025 graduates"), "conflict"),
    (KnockoutDraft(type="location", value="Pune (on-site)"), "ok"),
    (KnockoutDraft(type="location", value="Bengaluru (on-site)"), "unknown"),
    (KnockoutDraft(type="work_authorization", value="Must be authorised to work in India"), "unknown"),
])
def test_knockouts(rule, status):
    assert check_knockouts([rule], PROFILE)[0].status == status


def test_cgpa_unknown_without_cgpa_on_resume():
    profile = ResumeProfile(education=[{"institution": "X"}])
    assert check_knockouts([KnockoutDraft(type="cgpa", value="CGPA 7")], profile)[0].status == "unknown"


# ---------- score ----------

def m(kind: str, status: str) -> RequirementMatch:
    return RequirementMatch(requirement_id="r", text="t", kind=kind, status=status, reason="", decided_by="rules")


def test_jd_score_by_hand():
    matches = [m("must", "strong"), m("must", "listed_only"), m("must", "missing"), m("nice", "partial")]
    total, tier, _, subs = scoring.jd_score(matches, [], role_alignment=4, seniority="intern", min_years=None,
                                            is_student=True)
    by_key = {s.key: s.score for s in subs}
    assert by_key["must_coverage"] == 22.5      # 45 * 1.5 / 3
    assert by_key["nice_coverage"] == 7.5       # 15 * 0.5 / 1
    assert by_key["evidence_depth"] == 7.5      # 1 of 2 covered musts is proven
    assert by_key["experience_fit"] == 10 and by_key["knockouts"] == 10
    assert total == 62 and tier == "good"       # 22.5 + 7.5 + 7.5 + 10 + 4 + 10


def test_senior_role_for_a_student_gets_no_experience_points():
    sub = scoring.experience_fit("senior", 5, is_student=True)
    assert sub.score == 0


# ---------- end to end ----------

def setup_match(client) -> dict:
    resume_id = client.post("/api/v2/resumes", files={"file": ("Asha_Verma.pdf", builders.single_column_pdf())},
                            headers=auth()).json()["id"]
    jd_id = client.post("/api/v2/jds", json={"raw_text": SAMPLE_JD}, headers=auth()).json()["id"]
    resp = client.post("/api/v2/analyses", json={"resume_id": resume_id, "mode": "jd", "jd_id": jd_id},
                       headers=auth())
    assert resp.status_code == 202
    return client.get(f"/api/v2/analyses/{resp.json()['id']}", headers=auth()).json()


def test_jd_match_end_to_end(client, db):
    detail = setup_match(client)
    assert detail["status"] == "done", detail.get("error")
    result = detail["result"]
    assert result["kind"] == "jd"
    statuses = {r["text"]: r["status"] for r in result["requirements"]}
    assert statuses["Strong programming skills in Python"] == "strong"          # proven via FastAPI bullet
    assert statuses["Familiarity with Docker"] == "listed_only"                 # in skills, no bullet
    assert statuses["Exposure to message queues such as Kafka"] == "missing"
    knockouts = {k["type"]: k["status"] for k in result["knockouts"]}
    assert knockouts == {"cgpa": "ok", "grad_year": "ok", "location": "unknown"}
    assert result["tier"] in {"strong", "good", "stretch", "not_a_fit"}
    for evidence in (e for r in result["requirements"] for e in r["evidence"]):
        assert evidence["text"]                                                  # always a quoted bullet
    gaps = [g["skill"] for g in db.tables["skill_gaps"].values()]
    assert "Kafka" in gaps


def test_summary_lists_recent_analyses_and_open_gaps(client):
    detail = setup_match(client)
    summary = client.get("/api/v2/resume/summary", headers=auth()).json()
    assert summary["resume_count"] == 1
    assert summary["recent"][0]["id"] == detail["id"] and summary["recent"][0]["mode"] == "jd"
    assert summary["recent"][0]["jd_title"] == "Backend Engineering Intern"
    assert "Kafka" in summary["top_gaps"]


def test_jd_mode_needs_a_ready_jd(client):
    resume_id = client.post("/api/v2/resumes", files={"file": ("Asha_Verma.pdf", builders.single_column_pdf())},
                            headers=auth()).json()["id"]
    resp = client.post("/api/v2/analyses", json={"resume_id": resume_id, "mode": "jd"}, headers=auth())
    assert resp.status_code == 422
