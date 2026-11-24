"""
Legacy readiness radar for the old dashboard: resume, interview and usage breadth.
Replaced by the dashboard service in the dashboard rebuild.
"""

from __future__ import annotations

from app.core.db import get_db
from app.interview.summary import recent_scores as recent_interview_scores
from app.resume.summary import recent_general_scores


class CareerIntelligenceService:
    def get_readiness_radar(self, user_id: str) -> dict[str, int]:
        """Scores (0-100) for a 3-point radar: resume quality, interview performance, consistency."""
        # 1. Resume: average of the latest resume v2 general reviews
        try:
            resume_history = recent_general_scores(get_db(), user_id)
        except Exception:  # legacy demo user ids are not UUIDs
            resume_history = []
        resume_score = int(sum(resume_history) / len(resume_history)) if resume_history else 0

        # 2. Interview: average of the latest interview v2 sessions
        try:
            interview_history = recent_interview_scores(get_db(), user_id)
        except Exception:  # legacy demo user ids are not UUIDs
            interview_history = []
        interview_score = int(sum(interview_history) / len(interview_history)) if interview_history else 0

        # 3. Consistency: how many of the two practice areas have been used (0, 50 or 100)
        consistency_score = 50 * (bool(resume_history) + bool(interview_history))

        return {"resume": resume_score, "interview": interview_score, "consistency": consistency_score}


intelligence_service = CareerIntelligenceService()
