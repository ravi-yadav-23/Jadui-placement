"""User Sync Service: Ensures profiles, roles, and cross-module insights are synchronized."""

from __future__ import annotations

import logging
from typing import Any
from app.core.supabase_client import get_supabase_admin_client

logger = logging.getLogger(__name__)


class UserSyncService:
    def ensure_profile(self, user_id: str, email: str, full_name: str | None = None) -> dict:
        """Upserts a user profile into the profiles table."""
        client = get_supabase_admin_client()
        resp = client.table("profiles").select("*").eq("id", user_id).execute()

        if not resp.data:
            payload = {
                "id": user_id,
                "email": email,
                "full_name": full_name or email.split("@")[0],
                "role": "student",  # Default role
            }
            res = client.table("profiles").insert(payload).execute()
            return res.data[0] if res.data else {}

        return resp.data[0]


sync_service = UserSyncService()


def sync_resume_insights(user_id: str, skill_gaps: list[str]) -> None:
    """
    Cross-module sync: Updates global system state with gaps found in the latest resume analysis.
    """
    if not user_id or user_id == "demo-user-001":
        return

    try:
        from modules.system_ai.services import service as system_service

        current_state = system_service.get_state(user_id)
        existing_gaps = current_state.get("skill_gaps") or []

        # Merge unique gaps preserving order
        merged_gaps = list(dict.fromkeys(existing_gaps + [g for g in skill_gaps if g]))

        # Add a notification
        notifications = current_state.get("notifications") or []
        new_note = {
            "id": f"notif-resume-{len(notifications) + 1}",
            "title": "Resume Analyzed",
            "body": f"Detected {len(skill_gaps)} priority gap(s): {', '.join(skill_gaps[:3])}.",
            "read": False,
        }
        updated_notifications = [new_note] + [n for n in notifications if n.get("title") != "Resume Analyzed"][:9]

        system_service.save_state(
            user_id=user_id,
            tasks=current_state.get("tasks") or [],
            roadmap=current_state.get("roadmap") or [],
            notifications=updated_notifications,
            skill_gaps=merged_gaps[:12],
            chat_context=current_state.get("chat_context") or {},
            chat_history=current_state.get("chat_history") or [],
            chat_sessions=current_state.get("chat_sessions") or [],
            active_chat_session_id=current_state.get("active_chat_session_id") or "",
        )
    except Exception as e:
        logger.warning(f"sync_resume_insights failed: {e}")


def sync_interview_insights(user_id: str, interview_gaps: list[str]) -> None:
    """
    Cross-module sync: Updates global system state with communication and technical gaps from interview.
    """
    if not user_id or user_id == "demo-user-001":
        return

    try:
        from modules.system_ai.services import service as system_service

        current_state = system_service.get_state(user_id)
        existing_gaps = current_state.get("skill_gaps") or []

        merged_gaps = list(dict.fromkeys(existing_gaps + [g for g in interview_gaps if g]))

        notifications = current_state.get("notifications") or []
        new_note = {
            "id": f"notif-interview-{len(notifications) + 1}",
            "title": "Mock Interview Feedback",
            "body": f"Session evaluated. Recommended focus: {', '.join(interview_gaps[:2]) if interview_gaps else 'Practice more mocks.'}",
            "read": False,
        }
        updated_notifications = [new_note] + [n for n in notifications if n.get("title") != "Mock Interview Feedback"][:9]

        system_service.save_state(
            user_id=user_id,
            tasks=current_state.get("tasks") or [],
            roadmap=current_state.get("roadmap") or [],
            notifications=updated_notifications,
            skill_gaps=merged_gaps[:12],
            chat_context=current_state.get("chat_context") or {},
            chat_history=current_state.get("chat_history") or [],
            chat_sessions=current_state.get("chat_sessions") or [],
            active_chat_session_id=current_state.get("active_chat_session_id") or "",
        )
    except Exception as e:
        logger.warning(f"sync_interview_insights failed: {e}")


def sync_github_insights(user_id: str, profile_data: dict[str, Any]) -> None:
    """
    Cross-module sync: Ingests GitHub language stats and activity into chat_context for mentor personalization.
    """
    if not user_id or user_id == "demo-user-001" or not profile_data:
        return

    try:
        from modules.system_ai.services import service as system_service

        current_state = system_service.get_state(user_id)
        chat_context = current_state.get("chat_context") or {}

        top_langs = list((profile_data.get("langRepoCount") or {}).keys())[:5]
        gh_user = profile_data.get("user") or {}

        chat_context["githubUsername"] = gh_user.get("login") or chat_context.get("githubUsername")
        chat_context["github_tech_stack"] = top_langs or chat_context.get("github_tech_stack", [])
        chat_context["github_repos_count"] = profile_data.get("meta", {}).get("reposAnalyzed", 0)

        system_service.save_state(
            user_id=user_id,
            tasks=current_state.get("tasks") or [],
            roadmap=current_state.get("roadmap") or [],
            notifications=current_state.get("notifications") or [],
            skill_gaps=current_state.get("skill_gaps") or [],
            chat_context=chat_context,
            chat_history=current_state.get("chat_history") or [],
            chat_sessions=current_state.get("chat_sessions") or [],
            active_chat_session_id=current_state.get("active_chat_session_id") or "",
        )
    except Exception as e:
        logger.warning(f"sync_github_insights failed: {e}")
