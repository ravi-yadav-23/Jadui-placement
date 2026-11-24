"""Analysis runs (general review now, JD match later): create, cache, run in background, read.

Caching: the same profile + mode + JD + target role + prompt versions + model gives the
same `input_hash`. If a finished analysis with that hash exists, we return it instead of
paying for new LLM calls. That also makes results reproducible.
"""

from __future__ import annotations

import hashlib
import json
import logging

from app.core.config import settings
from app.core.db import Database, utc_now
from app.core.errors import AppError
from app.llm.client import PROMPT_VERSIONS, get_llm
from app.resume.pipeline.lint import lint_resume, unsupported_skills
from app.resume.pipeline.review import review_profile
from app.resume.pipeline.scoring import general_score
from app.resume.schemas import Check, Contacts, CreateAnalysis, GeneralReview, ResumeProfile
from app.resume.service import enforce_daily_limit, get_resume, is_stale

log = logging.getLogger(__name__)

PROMPTS_BY_MODE = {"general": ["resume_review"], "jd": ["jd_match"]}


def input_hash(profile: dict, request: CreateAnalysis, jd_text_hash: str | None) -> str:
    model = "fake" if settings.LLM_PROVIDER == "fake" else settings.LLM_PRIMARY_MODEL
    payload = {
        "profile": profile,
        "mode": request.mode,
        "target_role": (request.target_role or "").strip().lower(),
        "jd": jd_text_hash,
        "prompts": {name: PROMPT_VERSIONS[name] for name in PROMPTS_BY_MODE[request.mode]},
        "model": model,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def create_analysis(db: Database, user_id: str, request: CreateAnalysis) -> tuple[dict, bool]:
    """Returns (row, is_new). is_new=False means a cached finished analysis was returned."""
    resume = get_resume(db, user_id, request.resume_id)
    if resume["status"] != "ready" or not resume.get("profile"):
        raise AppError("not_ready", "The resume is still being processed.", 409)
    jd_hash = None
    if request.mode == "jd":
        raise AppError("not_implemented", "JD matching is not available yet.", 501)

    digest = input_hash(resume["profile"], request, jd_hash)
    cached = db.find_one("resume_analyses", user_id, input_hash=digest, status="done")
    if cached:
        return cached, False

    enforce_daily_limit(db, user_id, "resume_analyses", settings.DAILY_ANALYSIS_LIMIT)
    row = db.insert("resume_analyses", user_id, {
        "resume_id": request.resume_id,
        "jd_id": request.jd_id,
        "mode": request.mode,
        "target_role": request.target_role,
        "status": "queued",
        "input_hash": digest,
        "prompt_versions": {name: PROMPT_VERSIONS[name] for name in PROMPTS_BY_MODE[request.mode]},
    })
    return row, True


def run_analysis(db: Database, user_id: str, analysis_id: str) -> None:
    """Background job. Never raises: failures are written to the row."""
    row = db.update("resume_analyses", user_id, analysis_id, {"status": "running"})
    try:
        resume = get_resume(db, user_id, row["resume_id"])
        llm = get_llm(db, user_id)
        result = run_general_review(llm, resume, row.get("target_role"))
        db.update("resume_analyses", user_id, analysis_id, {
            "status": "done",
            "overall_score": result.overall_score,
            "sub_scores": [s.model_dump() for s in result.sub_scores],
            "result": result.model_dump(),
            "model": llm.last_model,
            "completed_at": utc_now(),
        })
    except AppError as exc:
        db.update("resume_analyses", user_id, analysis_id, {"status": "failed", "error": exc.message})
    except Exception:
        log.exception("analysis %s failed", analysis_id)
        db.update("resume_analyses", user_id, analysis_id, {"status": "failed", "error": "Analysis failed."})


def run_general_review(llm, resume: dict, target_role: str | None) -> GeneralReview:
    profile = ResumeProfile.model_validate(resume["profile"])
    checks = [Check.model_validate(c) for c in resume.get("checks") or []]
    contacts = Contacts.model_validate(resume.get("contacts") or {})

    bullets, strengths, top_actions = review_profile(llm, profile, target_role)
    unsupported = unsupported_skills(profile)
    overall, subs = general_score(checks, bullets, profile, contacts, len(unsupported))
    return GeneralReview(
        overall_score=overall,
        sub_scores=subs,
        bullets=bullets,
        findings=lint_resume(profile),
        strengths=strengths,
        top_actions=top_actions,
        ungrounded_count=sum(not b.grounded for b in profile.all_bullets()),
    )


def get_analysis(db: Database, user_id: str, analysis_id: str) -> dict:
    row = db.get("resume_analyses", user_id, analysis_id)
    if row is None:
        raise AppError("not_found", "Analysis not found", 404)
    if row["status"] in ("queued", "running") and is_stale(row["created_at"]):
        row = db.update("resume_analyses", user_id, analysis_id, {
            "status": "failed", "error": "The analysis was interrupted. Please run it again."})
    return row
