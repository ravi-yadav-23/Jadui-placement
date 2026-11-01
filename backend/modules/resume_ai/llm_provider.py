from typing import Any
from app.core.config import settings
from .utils import safe_json_from_text
from .section_parser import section_parser
from .evaluator import evaluator
from .prompts import (
    experience_review_prompt,
    leadership_review_prompt,
    personal_summary_review_prompt,
    projects_review_prompt,
    resume_cleanup_prompt,
    semantic_resume_analysis_prompt,
    technical_skills_review_prompt,
)

class LLMProvider:
    def _llm_json(self, prompt: str) -> dict[str, Any]:
        """
        Executes LLM call with a priority for Groq for resume analysis.
        """
        # Resume analysis performs best on Groq (Llama 3) for speed and JSON extraction
        if settings.GROQ_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.GROQ_API_KEY)
                resp = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return safe_json_from_text(resp.choices[0].message.content or "{}")
            except Exception as e:
                print(f"Groq primary failed, falling back: {e}")

        # Fallback to Gemini
        if settings.GEMINI_API_KEY:
            try:
                from app.shared.llm_client import generate_text
                raw = generate_text(prompt)
                return safe_json_from_text(raw)
            except Exception as e:
                print(f"Gemini fallback failed: {e}")

        return {}

    def llm_cleanup_resume(self, raw_resume_text: str) -> dict[str, Any]:
        prompt = resume_cleanup_prompt(raw_resume_text)
        return self._llm_json(prompt)

    def llm_semantic_analysis(self, resume_text: str, role_target: str, target_skills: list[str]) -> dict[str, Any]:
        prompt = semantic_resume_analysis_prompt(resume_text, role_target, target_skills)
        return self._llm_json(prompt)

    def llm_section_reviews(self, resume_text: str) -> list[dict[str, Any]]:
        sections = section_parser.extract_all_sections(resume_text)

        prompts: list[tuple[str, str]] = [
            ("personal_summary", personal_summary_review_prompt(sections.get("personal_summary") or resume_text[:2000])),
            ("technical_skills", technical_skills_review_prompt(sections.get("technical_skills") or resume_text[:2000])),
            ("experience", experience_review_prompt(sections.get("experience") or resume_text[:2500])),
            ("projects", projects_review_prompt(sections.get("projects") or resume_text[:2500])),
            ("leadership_achievements", leadership_review_prompt(sections.get("leadership_achievements") or resume_text[:1500])),
        ]

        reviews: list[dict[str, Any]] = []
        for section_key, prompt in prompts:
            try:
                data = self._llm_json(prompt)
                if isinstance(data, dict):
                    data["section"] = section_key
                    data["confidence"] = int(data.get("confidence", 78) or 78)
                    reviews.append(evaluator.sanitize_review_payload(data))
                else:
                    reviews.append(evaluator.deterministic_section_review(section_key, sections.get(section_key, ""), resume_text))
            except Exception:
                reviews.append(evaluator.deterministic_section_review(section_key, sections.get(section_key, ""), resume_text))
        return reviews

llm_provider = LLMProvider()
