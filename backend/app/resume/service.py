"""Orchestration: the API calls these functions; they call the pipeline steps and the database.

Long work (text extraction + LLM structuring) runs in a background task:
  POST /resumes  -> validate, store file, insert row (status=queued) -> 202
  background     -> process_resume(): processing -> ready | failed
  frontend       -> polls GET /resumes/{id} until status is ready/failed
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.db import Database
from app.core.errors import AppError
from app.llm.client import get_llm
from app.resume.pipeline.checks import CheckContext, run_checks
from app.resume.pipeline.contacts import extract_contacts
from app.resume.pipeline.document import ExtractedDoc
from app.resume.pipeline.extract_docx import extract_docx
from app.resume.pipeline.extract_pdf import count_pdf_pages, extract_pdf
from app.resume.pipeline.ingest import MIME_TYPES, FileKind, sha256_hex, validate_upload
from app.resume.pipeline.sections import find_sections
from app.resume.pipeline.structure import reassign_ids, structure_resume
from app.resume.schemas import ResumeProfile

log = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=10)  # a job still "processing" after this was lost (e.g. server restart)


def _since(hours: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


def enforce_daily_limit(db: Database, user_id: str, table: str, limit: int) -> None:
    if db.count_since(table, user_id, _since(24)) >= limit:
        raise AppError("rate_limited", f"Daily limit reached ({limit}). Try again tomorrow.", 429)


# ---------- Upload ----------

def create_resume(db: Database, user_id: str, filename: str, data: bytes, title: str | None) -> tuple[dict, bool]:
    """Validate + store. Returns (row, is_new). Same file uploaded twice -> the existing row."""
    kind = validate_upload(data)
    digest = sha256_hex(data)
    existing = db.find_one("resumes", user_id, file_sha256=digest)
    if existing and existing["status"] != "failed":
        return existing, False
    if existing:  # same file failed before: let the user retry it
        return db.update("resumes", user_id, existing["id"], {"status": "queued", "error": None}), True

    enforce_daily_limit(db, user_id, "resumes", settings.DAILY_UPLOAD_LIMIT)
    page_count = count_pdf_pages(data) if kind == "pdf" else 0
    if page_count > settings.RESUME_MAX_PAGES:
        raise AppError("too_many_pages", f"Resumes are limited to {settings.RESUME_MAX_PAGES} pages.", 422)

    resume_id = str(uuid.uuid4())
    path = f"{user_id}/{resume_id}.{kind}"
    db.upload_file(path, data, MIME_TYPES[kind])
    row = db.insert("resumes", user_id, {
        "id": resume_id,
        "title": (title or filename or "Resume").strip()[:120],
        "storage_path": path,
        "file_sha256": digest,
        "mime_type": MIME_TYPES[kind],
        "page_count": page_count,
        "status": "queued",
    })
    return row, True


def extract(kind: FileKind, data: bytes) -> ExtractedDoc:
    return extract_pdf(data) if kind == "pdf" else extract_docx(data)


def process_resume(db: Database, user_id: str, resume_id: str, data: bytes, filename: str = "") -> None:
    """Background job. Never raises: failures are written to the row for the UI to show."""
    db.update("resumes", user_id, resume_id, {"status": "processing"})
    try:
        kind = validate_upload(data)
        doc = extract(kind, data)
        contacts = extract_contacts(doc.text, doc.links)
        sections = find_sections(doc.lines)
        checks = run_checks(CheckContext(doc, contacts, sections, filename))
        if checks[0].id == "text_extractable" and checks[0].status == "fail":
            raise AppError("scanned_pdf", checks[0].message)

        # Save the deterministic results first: they stay visible even if the LLM step fails.
        db.update("resumes", user_id, resume_id, {
            "raw_text": doc.text,
            "extract_meta": {**doc.meta(), "filename": filename, "sections": list(sections.found)},
            "page_count": doc.page_count,
            "contacts": contacts.model_dump(),
            "checks": [c.model_dump() for c in checks],
        })
        profile = structure_resume(get_llm(db, user_id), doc.text, contacts)
        db.update("resumes", user_id, resume_id, {"profile": profile.model_dump(), "status": "ready"})
    except AppError as exc:
        db.update("resumes", user_id, resume_id, {"status": "failed", "error": exc.message})
    except Exception:
        log.exception("process_resume failed for %s", resume_id)
        db.update("resumes", user_id, resume_id, {"status": "failed", "error": "Could not process this file."})


# ---------- Read / delete ----------

def get_resume(db: Database, user_id: str, resume_id: str) -> dict:
    row = db.get("resumes", user_id, resume_id)
    if row is None:
        raise AppError("not_found", "Resume not found", 404)
    if row["status"] in ("queued", "processing") and is_stale(row["created_at"]):
        row = db.update("resumes", user_id, resume_id, {
            "status": "failed", "error": "Processing was interrupted. Please upload the file again.",
        })
    return row


def is_stale(created_at: str) -> bool:
    return datetime.fromisoformat(created_at) < datetime.now(UTC) - STALE_AFTER


def update_profile(db: Database, user_id: str, resume_id: str, profile: ResumeProfile) -> dict:
    """The user corrected the extracted profile (wrong section, missed bullet, typo from parsing)."""
    row = get_resume(db, user_id, resume_id)
    if row["status"] != "ready":
        raise AppError("not_ready", "The resume is still being processed.", 409)
    cleaned = reassign_ids(profile)
    return db.update("resumes", user_id, resume_id, {"profile": cleaned.model_dump(), "profile_edited": True})


def delete_resume(db: Database, user_id: str, resume_id: str) -> None:
    row = get_resume(db, user_id, resume_id)
    db.delete_file(row["storage_path"])
    db.delete("resumes", user_id, resume_id)  # analyses cascade in the database
