"""Gemini-powered mentor replies (shared key with interview module on Render)."""

from __future__ import annotations

import os
from typing import Any
from fastapi import HTTPException
from app.core.config import settings

class MentorService:
    def generate_reply(self, system_prompt: str, history: list[dict[str, Any]], message: str) -> str:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured on backend")

        from app.shared.llm_client import generate_text

        full_prompt = self._build_prompt(system_prompt, history, message)
        try:
            text = generate_text(
                full_prompt,
                temperature=settings.MENTOR_TEMPERATURE,
                max_output_tokens=settings.MENTOR_MAX_OUTPUT_TOKENS
            ).strip()
            if not text:
                raise HTTPException(status_code=502, detail="Empty model response")
            return text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    def _build_prompt(self, system_prompt: str, history: list[dict[str, Any]], message: str) -> str:
        lines: list[str] = [
            system_prompt.strip(),
            "",
            "---",
            "Conversation:",
            "",
        ]
        for h in history[-16:]:
            role = (h.get("role") or "user").lower()
            content = str(h.get("content") or "").strip()
            if not content:
                continue
            if role == "assistant":
                lines.append(f"Assistant: {content}")
            else:
                lines.append(f"User: {content}")
        lines.append("")
        lines.append(
            "User: Latest question (answer this specifically; do not repeat generic advice):\n"
            + message.strip()[:8000]
        )
        lines.append("")
        lines.append("Assistant:")
        return "\n".join(lines)


service = MentorService()
