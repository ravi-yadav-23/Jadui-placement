from datetime import UTC, datetime, timedelta

from app.core.config import settings
from tests.resume import builders
from tests.resume.conftest import auth


def upload(client, data: bytes, name: str = "Asha_Verma_Resume.pdf", user: str = "user-a"):
    return client.post("/api/v2/resumes", files={"file": (name, data)}, headers=auth(user))


def test_upload_then_poll_until_ready(client, db):
    resp = upload(client, builders.single_column_pdf())
    assert resp.status_code == 202
    body = resp.json()
    assert body["title"] == "Asha_Verma_Resume.pdf"

    # TestClient runs background tasks before returning, so processing is already done.
    detail = client.get(f"/api/v2/resumes/{body['id']}", headers=auth()).json()
    assert detail["status"] == "ready"
    assert detail["raw_text"].startswith("Asha Verma\n")
    assert detail["extract_meta"]["columns"] == 1
    assert f"user-a/{body['id']}.pdf" in db.files  # original kept in storage


def test_same_file_twice_returns_existing_row(client):
    data = builders.single_column_pdf()
    first = upload(client, data).json()
    second = upload(client, data)
    assert second.status_code == 200
    assert second.json()["id"] == first["id"]


def test_other_users_cannot_read_or_delete(client):
    resume_id = upload(client, builders.single_column_pdf()).json()["id"]
    assert client.get(f"/api/v2/resumes/{resume_id}", headers=auth("user-b")).status_code == 404
    assert client.delete(f"/api/v2/resumes/{resume_id}", headers=auth("user-b")).status_code == 404
    assert client.get(f"/api/v2/resumes/{resume_id}", headers=auth()).status_code == 200


def test_unsupported_file_is_rejected(client):
    resp = upload(client, b"just some text", name="resume.txt")
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "unsupported_type"


def test_delete_removes_row_and_file(client, db):
    resume_id = upload(client, builders.single_column_pdf()).json()["id"]
    assert client.delete(f"/api/v2/resumes/{resume_id}", headers=auth()).status_code == 204
    assert client.get(f"/api/v2/resumes/{resume_id}", headers=auth()).status_code == 404
    assert db.files == {}


def test_daily_upload_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "DAILY_UPLOAD_LIMIT", 1)
    assert upload(client, builders.single_column_pdf()).status_code == 202
    resp = upload(client, builders.two_column_pdf())
    assert resp.status_code == 429


def test_job_lost_in_a_restart_is_reported_as_failed(client, db):
    old = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    row = db.insert("resumes", "user-a", {"title": "x", "storage_path": "p", "file_sha256": "h",
                                          "mime_type": "application/pdf", "page_count": 1,
                                          "status": "processing", "created_at": old})
    detail = client.get(f"/api/v2/resumes/{row['id']}", headers=auth()).json()
    assert detail["status"] == "failed"
