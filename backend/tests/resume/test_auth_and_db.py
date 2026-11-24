from app.core.db import InMemoryDatabase
from tests.resume.conftest import auth, make_token


def test_missing_token_is_rejected(client):
    resp = client.get("/api/v2/resumes")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "not_authenticated"


def test_expired_token_is_rejected(client):
    headers = {"Authorization": f"Bearer {make_token('user-a', expires_in=-10)}"}
    resp = client.get("/api/v2/resumes", headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "token_expired"


def test_wrong_signature_is_rejected(client):
    forged = make_token("user-a", secret="some-other-secret-that-is-32-bytes-long!!")
    resp = client.get("/api/v2/resumes", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_token"


def test_valid_token_returns_empty_list(client):
    resp = client.get("/api/v2/resumes", headers=auth())
    assert resp.status_code == 200
    assert resp.json() == []


def test_users_never_see_each_others_rows():
    db = InMemoryDatabase()
    row = db.insert("resumes", "user-a", {"title": "A's resume"})
    assert db.get("resumes", "user-b", row["id"]) is None
    assert db.list("resumes", "user-b") == []
    assert db.update("resumes", "user-b", row["id"], {"title": "hacked"}) is None
    db.delete("resumes", "user-b", row["id"])
    assert db.get("resumes", "user-a", row["id"])["title"] == "A's resume"
