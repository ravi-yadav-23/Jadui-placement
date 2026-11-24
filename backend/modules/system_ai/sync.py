"""Legacy cross-module sync: copies interview gaps into the old system state (replaced in the interview rebuild)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


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
