"""The coach: one LLM call per message, grounded in a server-built context, with checked action proposals.

    reply = send(db, user_id, "I finished the deadlocks task, what next?")

Safety (OWASP LLM06 "excessive agency"):
  * the coach can only PROPOSE actions from a fixed list; each is a button the student must click
  * proposals are validated here: task ids must exist in the context, dates must be inside the plan,
    interview tracks and topics come from fixed lists; anything else is dropped
  * clicking a button calls the normal, authorised API (the coach has no write access of its own)
"""

from __future__ import annotations

import json
from datetime import date

from app.coach.context import build_context
from app.coach.schemas import CoachAction, CoachDraft
from app.core.config import settings
from app.core.db import Database
from app.llm.client import get_llm
from app.resume.service import enforce_daily_limit

HISTORY_MESSAGES = 10
MAX_ACTIONS = 3


def list_messages(db: Database, user_id: str, limit: int = 50) -> list[dict]:
    rows = db.list("coach_messages", user_id, limit=limit)
    return sorted(rows, key=lambda r: r["created_at"])


def send(db: Database, user_id: str, content: str) -> dict:
    # Two rows per exchange (question + reply), so the daily message limit counts pairs.
    enforce_daily_limit(db, user_id, "coach_messages", settings.COACH_DAILY_MESSAGES * 2)
    context = build_context(db, user_id)
    history = list_messages(db, user_id, limit=HISTORY_MESSAGES)
    draft = get_llm(db, user_id).structured("coach", CoachDraft, {
        "context_json": json.dumps(context, indent=1, default=str),
        "history": "\n".join(f"{m['role']}: {m['content']}" for m in history) or "(none)",
        "message": content.strip(),
    }, temperature=0.4)
    db.insert("coach_messages", user_id, {"role": "user", "content": content.strip(), "actions": []})
    return db.insert("coach_messages", user_id, {
        "role": "assistant",
        "content": draft.reply.strip(),
        "actions": [a.model_dump(mode="json") for a in valid_actions(draft.actions, context)],
    })


def valid_actions(actions: list[CoachAction], context: dict) -> list[CoachAction]:
    plan = context.get("plan") or {}
    tasks = {t["id"]: t for t in plan.get("tasks", [])}
    today = date.fromisoformat(context["today"])
    target = date.fromisoformat(plan["target_date"]) if plan.get("target_date") else None
    kept: list[CoachAction] = []
    for action in actions:
        ok = {
            "open_page": action.page is not None,
            "start_interview": action.track is not None,
            "mark_task_done": action.task_id in tasks and tasks[action.task_id]["status"] == "todo",
            "move_task": (action.task_id in tasks and tasks[action.task_id]["status"] == "todo"
                          and action.date is not None and target is not None and today <= action.date <= target),
            "replan": bool(plan),
        }[action.type]
        if ok:
            kept.append(action.model_copy(update={"label": action.label.strip()[:40] or "Open"}))
    return kept[:MAX_ACTIONS]


def clear(db: Database, user_id: str) -> None:
    db.delete_all("coach_messages", user_id)
