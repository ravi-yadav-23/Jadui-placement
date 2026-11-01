"""Service layer for AI interview generation, evaluation, and scoring."""

from __future__ import annotations

import os
from statistics import mean
from typing import Any

from fastapi import HTTPException
from app.core.config import settings
from app.core.supabase_client import get_supabase_admin_client
from .prompts import answer_evaluation_prompt, question_generation_prompt
from .utils import (
    AnswerEvaluation,
    clamp_score,
    new_session_id,
)
from app.shared.json_parser import extract_json_from_llm_response
from app.shared.db_helpers import fetch_user_history
from .repository import repository
from .question_bank import question_bank


class InterviewAIService:
    """
    Extracted and refactored from PulseAI interview generation/evaluation flows:
    - question generation logic (PulseAI generate route)
    - feedback + scoring logic (PulseAI createFeedback action)
    """

    def _resolve_interview_provider(self) -> str:
        """
        Interview flows prefer Gemini when GEMINI_API_KEY is set (unless overridden).
        Set INTERVIEW_AI_PROVIDER=openai to force OpenAI even if a Gemini key exists.
        """
        explicit = os.getenv("INTERVIEW_AI_PROVIDER", "").strip().lower()
        if explicit in ("gemini", "openai"):
            return explicit
        if os.getenv("GEMINI_API_KEY"):
            return "gemini"
        return os.getenv("AI_PROVIDER", "openai").strip().lower()

    def _llm_generate(self, prompt: str) -> str:
        # 1. Prefer Gemini for Interview flows
        if settings.GEMINI_API_KEY:
            try:
                from app.shared.llm_client import generate_text
                return generate_text(prompt)
            except Exception as e:
                print(f"Interview Gemini primary failed: {e}")

        # 2. Fallback to OpenAI
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                model = "gpt-4o-mini" # default fallback
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                print(f"Interview OpenAI fallback failed: {e}")

        return ""

    def _fallback_question_set(self, role_title: str, skills: list[str] | None = None, question_count: int = 5) -> list[str]:
        qs = question_bank.get_fallback_question_set(role_title)
        if question_count and len(qs) > question_count:
            return qs[:question_count]
        return qs

    def _fallback_evaluation(self, question: str, answer: str, skills: list[str]) -> dict[str, Any]:
        answer_l = answer.lower()
        answer_words = len(answer.split())
        keyword_hits = sum(1 for skill in skills if skill.lower() in answer_l)
        has_structure = any(token in answer_l for token in ["first", "then", "finally", "because", "therefore"])
        has_metrics = bool(any(ch.isdigit() for ch in answer) or "%" in answer)
        has_debug_terms = any(token in answer_l for token in ["logs", "metrics", "trace", "rollback", "monitor"])

        clarity = 35 if answer_words < 15 else 62 if answer_words < 35 else 78
        if has_structure:
            clarity += 6
        relevance = 45 + min(keyword_hits * 12, 30)
        if "debug" in question.lower() and has_debug_terms:
            relevance += 10
        correctness = 50 if answer_words < 12 else 66
        if has_metrics:
            correctness += 8

        strengths: list[str] = []
        if has_structure:
            strengths.append("Answer has a visible structure and logical flow.")
        if keyword_hits > 0:
            strengths.append("Response references role-relevant technologies.")
        if has_metrics:
            strengths.append("Includes measurable signal, improving credibility.")
        if not strengths:
            strengths.append("Basic relevance is present, but depth is limited.")

        gaps: list[str] = []
        if not has_structure:
            gaps.append("Lacks clear structure (context -> action -> result).")
        if not has_metrics:
            gaps.append("Missing measurable impact (latency, throughput, reliability, % improvement).")
        if keyword_hits == 0 and skills:
            gaps.append("Does not connect answer to expected skill stack.")

        q_lower = question.lower()
        if "debug" in q_lower:
            model_hint = "A strong answer should cover reproduction, hypothesis, logs/metrics, root cause, fix, and prevention."
        elif "challenging problem" in q_lower:
            model_hint = "A strong answer should state problem constraints, design decision, trade-off, and measurable outcome."
        else:
            model_hint = "A strong answer should include context, technical implementation detail, and quantifiable result."

        return {
            "correctness": clamp_score(correctness),
            "clarity": clamp_score(clarity),
            "relevance": clamp_score(relevance),
            "feedback": (
                f"For '{question}', your response covers basics but lacks interview-grade depth. "
                "Add implementation detail, explicit trade-offs, and quantified impact."
            ),
            "strengths": strengths[:3],
            "gaps": gaps[:3],
            "suggestions": [
                "Use PAR/STAR structure: problem, action, result.",
                "Mention concrete tools, architecture choices, and constraints.",
                "Add one measurable metric to prove impact.",
            ],
            "model_answer_hint": model_hint,
        }

    def _get_session_row(self, session_id: str) -> dict[str, Any]:
        return repository.get_session_row(session_id)

    def _get_answer_rows(self, session_id: str) -> list[dict[str, Any]]:
        return repository.get_answer_rows(session_id)

    def start_interview(
        self,
        role: str,
        skills: list[str],
        level: str = "not specified",
        interview_type: str = "mixed",
        question_count: int = 5,
        user_id: str = None,
    ) -> dict[str, Any]:
        if not role:
            raise HTTPException(status_code=400, detail="role is required")
        if question_count <= 0 or question_count > 20:
            raise HTTPException(status_code=400, detail="question_count must be between 1 and 20")

        prompt = question_generation_prompt(role, skills, level, interview_type, question_count)

        questions: list[str]
        try:
            raw = self._llm_generate(prompt)
            parsed = extract_json_from_llm_response(raw)
            questions = parsed.get("questions", [])
            if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
                raise ValueError("Invalid questions format")
            questions = questions[:question_count]
            if len(questions) < question_count:
                questions.extend(self._fallback_question_set(role))
        except Exception:
            questions = self._fallback_question_set(role)

        session_id = new_session_id()
        payload = {
            "id": session_id,
            "role": role,
            "skills": skills,
            "level": level,
            "interview_type": interview_type,
            "questions": questions,
            "user_id": user_id,
        }
        repository.create_session(payload)
        return {
            "session_id": session_id,
            "role": role,
            "skills": skills,
            "level": level,
            "interview_type": interview_type,
            "questions": questions,
        }

    def submit_answer(self, session_id: str, question_index: int, answer: str, user_id: str) -> AnswerEvaluation:
        session = self._get_session_row(session_id)
        if session.get("user_id") and session.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        questions = session.get("questions") or []
        if question_index < 0 or question_index >= len(questions):
            raise HTTPException(status_code=400, detail="Invalid question_index")
        if not answer or not answer.strip():
            raise HTTPException(status_code=400, detail="answer is required")

        question = questions[question_index]
        prompt = answer_evaluation_prompt(
            question,
            answer,
            session.get("role", ""),
            session.get("skills") or [],
        )

        try:
            raw = self._llm_generate(prompt)
            data = extract_json_from_llm_response(raw)
        except Exception:
            data = self._fallback_evaluation(question, answer, session.get("skills") or [])

        correctness = clamp_score(data.get("correctness", 0))
        clarity = clamp_score(data.get("clarity", 0))
        relevance = clamp_score(data.get("relevance", 0))
        overall = clamp_score(mean([correctness, clarity, relevance]))
        feedback = str(data.get("feedback", "")).strip() or "Answer needs stronger technical depth and structure."
        strengths = [str(item).strip() for item in data.get("strengths", []) if str(item).strip()][:3]
        gaps = [str(item).strip() for item in data.get("gaps", []) if str(item).strip()][:3]
        suggestions = [str(item).strip() for item in data.get("suggestions", []) if str(item).strip()][:5]
        model_answer_hint = str(data.get("model_answer_hint", "")).strip()
        if strengths:
            feedback = f"{feedback} Strength: {strengths[0]}"
        if gaps:
            feedback = f"{feedback} Gap: {gaps[0]}"
        if model_answer_hint:
            suggestions = suggestions + [f"Model answer hint: {model_answer_hint}"]
        suggestions = suggestions[:5]

        evaluation = AnswerEvaluation(
            correctness=correctness,
            clarity=clarity,
            relevance=relevance,
            overall=overall,
            feedback=feedback,
            suggestions=suggestions,
            question_index=question_index,
            question=question,
            answer=answer.strip(),
        )
        repository.save_answer({
            "session_id": session_id,
            "question_index": question_index,
            "question": question,
            "answer": evaluation.answer,
            "correctness": evaluation.correctness,
            "clarity": evaluation.clarity,
            "relevance": evaluation.relevance,
            "overall": evaluation.overall,
            "feedback": evaluation.feedback,
            "suggestions": evaluation.suggestions,
        })
        return evaluation

    def get_result(self, session_id: str, user_id: str) -> dict[str, Any]:
        session = self._get_session_row(session_id)
        if session.get("user_id") and session.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        answers = self._get_answer_rows(session_id)

        if not answers:
            return {
                "session_id": session_id,
                "role": session.get("role", ""),
                "scores": {"correctness": 0, "clarity": 0, "relevance": 0, "overall": 0},
                "summary_feedback": "No answers submitted yet.",
                "answered_count": 0,
                "total_questions": len(session.get("questions") or []),
                "evaluations": [],
            }

        correctness_avg = clamp_score(mean(int(item.get("correctness", 0)) for item in answers))
        clarity_avg = clamp_score(mean(int(item.get("clarity", 0)) for item in answers))
        relevance_avg = clamp_score(mean(int(item.get("relevance", 0)) for item in answers))
        overall_avg = clamp_score(mean(int(item.get("overall", 0)) for item in answers))

        return {
            "session_id": session_id,
            "role": session.get("role", ""),
            "scores": {
                "correctness": correctness_avg,
                "clarity": clarity_avg,
                "relevance": relevance_avg,
                "overall": overall_avg,
            },
            "summary_feedback": "Focus on concise structure, role-relevant examples, and technical depth.",
            "answered_count": len(answers),
            "total_questions": len(session.get("questions") or []),
            "evaluations": answers,
        }

    def generate_feedback_from_transcript(
        self,
        session_id: str,
        user_id: str,
        transcript: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyzes the full conversation for a live interview session.
        Returns a scorecard and triggers global status sync.
        """
        if not transcript:
            return {
                "score": 0,
                "summary": "No transcript data received.",
                "strengths": [],
                "improvements": ["Try to speak more during the session."],
                "answers": []
            }
            
        # 1. Simple Scoring Logic based on word count and technicality
        text_blob = " ".join([m.get("content") or m.get("text", "") for m in transcript]).lower()
        word_count = len(text_blob.split())
        
        # Heuristic: Depth and Clarity
        score = min(95, max(40, 60 + (word_count // 20))) 
        
        # 2. Extract potential gaps (Simulation for now, or based on transcript length)
        gaps = ["Technical Depth", "Structure"]
        if word_count < 100:
            gaps.append("Elaboration")
            
        # 3. Create Result Object
        feedback = {
            "score": score,
            "summary": f"Your interview showed { 'good' if score > 70 else 'fair' } engagement with {word_count} words spoken.",
            "strengths": ["Active Participation", "Verbal Communication"],
            "improvements": gaps,
            "answers": transcript # Storing full log
        }
        
        # 4. Global synchronization Trigger
        try:
            from modules.system_ai.sync import sync_interview_insights
            sync_interview_insights(user_id, gaps)
        except Exception as e:
            print(f"Interview sync failed: {e}")
            
        return feedback

    def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        sessions = repository.get_history(user_id, limit)
        history: list[dict[str, Any]] = []
        for session in sessions:
            session_id = session.get("id")
            answers = self._get_answer_rows(session_id)
            if answers:
                overall = clamp_score(mean(int(item.get("overall", 0)) for item in answers))
            else:
                overall = 0
            history.append(
                {
                    "session_id": session_id,
                    "role": session.get("role", ""),
                    "level": session.get("level", ""),
                    "interview_type": session.get("interview_type", ""),
                    "skills": session.get("skills") or [],
                    "overall_score": overall,
                    "answered_count": len(answers),
                    "total_questions": len(session.get("questions") or []),
                    "created_at": session.get("created_at", ""),
                }
            )
        return history


service = InterviewAIService()
