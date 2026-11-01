from typing import Any
from fastapi import HTTPException
from app.core.supabase_client import get_supabase_admin_client
from app.shared.db_helpers import fetch_user_history

class SessionRepository:
    def get_session_row(self, session_id: str) -> dict[str, Any]:
        supabase = get_supabase_admin_client()
        resp = (
            supabase.table("interview_sessions")
            .select("*")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Interview session not found")
        return rows[0]

    def get_answer_rows(self, session_id: str) -> list[dict[str, Any]]:
        supabase = get_supabase_admin_client()
        resp = (
            supabase.table("interview_answers")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        return resp.data or []

    def create_session(self, payload: dict[str, Any]) -> None:
        supabase = get_supabase_admin_client()
        supabase.table("interview_sessions").insert(payload).execute()

    def update_session(self, session_id: str, payload: dict[str, Any]) -> None:
        supabase = get_supabase_admin_client()
        supabase.table("interview_sessions").update(payload).eq("id", session_id).execute()

    def save_answer(self, payload: dict[str, Any]) -> None:
        supabase = get_supabase_admin_client()
        supabase.table("interview_answers").insert(payload).execute()

    def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        return fetch_user_history("interview_sessions", user_id, limit)

repository = SessionRepository()
