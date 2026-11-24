"""Delete all of a user's data (the "Delete my data" button in Settings).

Child tables first, then parents, then the uploaded files. The Supabase account itself is managed by
Supabase Auth and is not deleted here.
"""

from __future__ import annotations

from app.core.db import Database

TABLES = [
    "coach_messages", "plan_tasks", "plan_topics", "plan_checkins", "plans", "planner_profiles",
    "interview_turns", "interviews", "skill_gaps", "resume_analyses", "job_descriptions", "resumes", "llm_calls",
]


def delete_all_data(db: Database, user_id: str) -> None:
    paths = [r["storage_path"] for r in db.list("resumes", user_id, columns="storage_path,created_at", limit=500)
             if r.get("storage_path")]
    for table in TABLES:
        db.delete_all(table, user_id)
    for path in paths:
        db.delete_file(path)
