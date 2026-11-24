"""Job description library: save a pasted JD once, parse it once, reuse it for many matches."""

import logging

from app.core.db import Database
from app.core.errors import AppError
from app.llm.client import get_llm
from app.resume.pipeline.ingest import sha256_hex
from app.resume.pipeline.jd_parse import parse_jd
from app.resume.schemas import CreateJd
from app.resume.service import is_stale

log = logging.getLogger(__name__)


def create_jd(db: Database, user_id: str, request: CreateJd) -> tuple[dict, bool]:
    text = request.raw_text.strip()
    digest = sha256_hex(text.encode("utf-8"))
    existing = db.find_one("job_descriptions", user_id, text_sha256=digest)
    if existing and existing["status"] != "failed":
        return existing, False
    if existing:
        return db.update("job_descriptions", user_id, existing["id"], {"status": "queued", "error": None}), True
    row = db.insert("job_descriptions", user_id, {
        "title": request.title, "company": request.company, "raw_text": text,
        "text_sha256": digest, "status": "queued",
    })
    return row, True


def process_jd(db: Database, user_id: str, jd_id: str) -> None:
    """Background job. Never raises."""
    row = db.update("job_descriptions", user_id, jd_id, {"status": "processing"})
    try:
        parsed = parse_jd(get_llm(db, user_id), row["raw_text"])
        db.update("job_descriptions", user_id, jd_id, {
            "parsed": parsed.model_dump(),
            "title": row.get("title") or parsed.title,       # the user's own title wins
            "company": row.get("company") or parsed.company,
            "status": "ready",
        })
    except AppError as exc:
        db.update("job_descriptions", user_id, jd_id, {"status": "failed", "error": exc.message})
    except Exception:
        log.exception("JD parse failed for %s", jd_id)
        db.update("job_descriptions", user_id, jd_id, {"status": "failed", "error": "Could not read this JD."})


def get_jd(db: Database, user_id: str, jd_id: str) -> dict:
    row = db.get("job_descriptions", user_id, jd_id)
    if row is None:
        raise AppError("not_found", "Job description not found", 404)
    if row["status"] in ("queued", "processing") and is_stale(row["created_at"]):
        row = db.update("job_descriptions", user_id, jd_id, {
            "status": "failed", "error": "Parsing was interrupted. Please add the JD again."})
    return row
