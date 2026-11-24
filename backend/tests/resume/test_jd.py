from app.resume.pipeline.jd_parse import build_requirements
from app.resume.schemas import JdDraft
from tests.resume.builders import SAMPLE_JD
from tests.resume.conftest import auth


def test_requirements_get_ids_and_canonical_skills():
    draft = JdDraft.model_validate({"title": "Backend Intern", "requirements": [
        {"text": "Experience with postgres and REST APIs", "kind": "must", "skills": ["postgres"]},
        {"text": "Kubernetes is a plus", "kind": "nice", "skills": []},
    ]})
    parsed = build_requirements(draft, "Experience with postgres and REST APIs. Kubernetes is a plus.")
    assert [(r.id, r.kind, r.skills) for r in parsed.requirements] == [
        ("r0", "must", ["PostgreSQL", "REST APIs"]),   # alias normalised + the skill the LLM forgot
        ("r1", "nice", ["Kubernetes"]),
    ]


def test_knockouts_not_in_the_jd_text_are_dropped():
    draft = JdDraft.model_validate({"title": "Intern", "min_years": 2, "knockouts": [
        {"type": "cgpa", "value": "Minimum CGPA 7.5"},
        {"type": "grad_year", "value": "2025 batch"},          # hallucinated: the JD says 2026
    ]})
    parsed = build_requirements(draft, SAMPLE_JD)
    assert [k.value for k in parsed.knockouts] == ["Minimum CGPA 7.5"]
    assert parsed.min_years is None                              # "2 years" is not in the JD


def test_create_and_parse_jd_via_api(client):
    resp = client.post("/api/v2/jds", json={"raw_text": SAMPLE_JD}, headers=auth())
    assert resp.status_code == 202
    detail = client.get(f"/api/v2/jds/{resp.json()['id']}", headers=auth()).json()
    assert detail["status"] == "ready"
    assert detail["title"] == "Backend Engineering Intern"       # filled from the parse
    parsed = detail["parsed"]
    kinds = {r["text"]: r["kind"] for r in parsed["requirements"]}
    assert kinds["Strong programming skills in Python"] == "must"
    assert kinds["Experience with Kubernetes"] == "nice"
    assert {k["type"] for k in parsed["knockouts"]} == {"cgpa", "grad_year", "location"}


def test_same_jd_twice_is_reused_and_private(client):
    first = client.post("/api/v2/jds", json={"raw_text": SAMPLE_JD}, headers=auth()).json()
    again = client.post("/api/v2/jds", json={"raw_text": SAMPLE_JD}, headers=auth())
    assert again.status_code == 200 and again.json()["id"] == first["id"]
    assert client.get(f"/api/v2/jds/{first['id']}", headers=auth("user-b")).status_code == 404


def test_too_short_jd_is_rejected(client):
    assert client.post("/api/v2/jds", json={"raw_text": "Python dev"}, headers=auth()).status_code == 422
