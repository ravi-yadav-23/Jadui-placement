"""Deterministic analysis + optional LLM enhancement for resume intelligence."""

from __future__ import annotations
from typing import Any

from .utils import normalize_space
from .constants import SECTION_KEYS
from .section_parser import section_parser
from .evaluator import evaluator
from .llm_provider import llm_provider

class ResumeAnalyzer:
    def _build_detailed_review(
        self,
        section_reviews: list[dict[str, Any]],
        overall_score_100: int,
    ) -> dict[str, Any]:
        section_map = {str(s.get("section", "")).strip(): s for s in section_reviews}
        ordered = [section_map.get(k, {"section": k, "bs_factor": 6, "issues": [], "improved_block": "", "justification": [], "tips": []}) for k in SECTION_KEYS]
        all_issues: list[str] = []
        all_justifications: list[str] = []
        all_tips: list[str] = []
        bs_factors: dict[str, int] = {}
        rewritten_sections: list[dict[str, str]] = []

        for section in ordered:
            section = evaluator.sanitize_review_payload(section)
            key = str(section.get("section", "unknown"))
            label = key.replace("_", " ").title()
            try:
                bs_value = int(section.get("bs_factor", 6))
            except Exception:
                bs_value = 6
            bs_factors[label] = max(1, min(10, bs_value))
            all_issues.extend([str(i) for i in (section.get("issues") or []) if str(i).strip()])
            all_justifications.extend([str(i) for i in (section.get("justification") or []) if str(i).strip()])
            all_tips.extend([str(i) for i in (section.get("tips") or []) if str(i).strip()])
            improved = str(section.get("improved_block", "")).strip()
            if improved:
                rewritten_sections.append({"section": label, "content": improved})

        unique_issues = [evaluator.sanitize_tone_line(i) for i in list(dict.fromkeys(all_issues))[:10]]
        unique_issues = [i for i in unique_issues if i]
        unique_justifications = [evaluator.sanitize_tone_line(i) for i in list(dict.fromkeys(all_justifications))[:6]]
        unique_justifications = [i for i in unique_justifications if i]
        unique_tips = [evaluator.sanitize_tone_line(i) for i in list(dict.fromkeys(all_tips))[:4]]
        unique_tips = [i for i in unique_tips if i]
        overall_score_10 = round(max(1.0, min(10.0, overall_score_100 / 10.0)), 1)
        avg_bs = sum(bs_factors.values()) / max(1, len(bs_factors))
        if overall_score_10 >= 7.5:
            competitive = "Above average profile for startups; needs sharper impact language for top-tier screening."
        elif overall_score_10 >= 6:
            competitive = "Average profile in current pool; credible but not differentiated enough for strong shortlist conversion."
        else:
            competitive = "Below competitive threshold right now; weak positioning and section depth will hurt shortlist chances."

        return {
            "brutal_assessment": {
                "overall_score_out_of_10": overall_score_10,
                "section_wise_bs_factor": bs_factors,
                "clear_flaws": unique_issues,
            },
            "optimized_output": rewritten_sections,
            "justification": unique_justifications or [
                "Weak phrasing reduced clarity.",
                "Technical impact was not visible enough for recruiter scan speed.",
                "Sections were rewritten for ATS readability and credibility.",
            ],
            "competitive_insight": competitive + f" Current BS intensity: {avg_bs:.1f}/10.",
            "actionable_next_steps": unique_tips or [
                "Rewrite summary with role + backend/API depth in 2-3 lines.",
                "Convert experience bullets to measurable impact.",
                "Reorder projects by technical depth and interview defensibility.",
            ],
        }

    def analyze(
        self,
        resume_text: str,
        role_target: str,
        target_skills: list[str],
        use_llm: bool = True,
    ) -> dict[str, Any]:
        raw_resume_text = resume_text or ""
        cleaned = normalize_space(raw_resume_text)
        cleanup_payload: dict[str, Any] = {}
        cleaned_for_analysis = raw_resume_text
        llm_skills_hint: list[str] = []
        llm_projects_hint: list[str] = []
        llm_experience_years = 0

        if use_llm:
            try:
                cleanup_payload = llm_provider.llm_cleanup_resume(cleaned[:12000])
                cleaned_for_analysis = str(
                    str(cleanup_payload.get("normalized_text", cleaned))
                ) or raw_resume_text
                llm_skills_hint = [
                    str(item).strip().lower()
                    for item in (cleanup_payload.get("skills") or [])
                    if str(item).strip()
                ]
                llm_projects_hint = [
                    str(item).strip()
                    for item in (cleanup_payload.get("projects") or [])
                    if str(item).strip()
                ]
                llm_experience_years = int(cleanup_payload.get("experience_years", 0) or 0)
            except Exception:
                cleaned_for_analysis = raw_resume_text

        deterministic_skills = section_parser.extract_skills(normalize_space(cleaned_for_analysis))
        skills = sorted(set(deterministic_skills + llm_skills_hint))
        projects = (section_parser.extract_projects(cleaned_for_analysis) + llm_projects_hint)[:5]
        if llm_experience_years > 0:
            exp = (
                "lead"
                if llm_experience_years >= 10
                else "senior"
                if llm_experience_years >= 6
                else "mid"
                if llm_experience_years >= 3
                else "junior"
            )
        else:
            exp = section_parser.infer_experience_level(normalize_space(cleaned_for_analysis))
        
        gap = evaluator.compute_skill_gap(skills, target_skills)
        quality_audit = evaluator.deterministic_quality_audit(cleaned_for_analysis)
        deterministic_base_score = quality_audit["score"] - (len(gap) * 5)
        deterministic_base_score = max(35, min(90, deterministic_base_score))

        deterministic = {
            "skills": skills,
            "projects": projects,
            "experience_level": exp,
            "strengths": [
                "Demonstrates relevant technical stack exposure." if skills else "Resume structure is present.",
                "Project descriptions show implementation context." if projects else "Profile provides baseline information.",
            ],
            "weaknesses": (
                (["Missing target skills: " + ", ".join(gap)] if gap else [])
                + quality_audit["issues"][:3]
            )[:5],
            "recommended_roles": [role_target] if role_target else ["Software Engineer"],
            "skill_gap": gap,
            "score": deterministic_base_score,
            "section_reviews": evaluator.fallback_section_reviews(cleaned_for_analysis),
        }
        deterministic["detailed_review"] = self._build_detailed_review(
            deterministic["section_reviews"], deterministic["score"]
        )

        if not use_llm:
            return deterministic

        try:
            semantic = llm_provider.llm_semantic_analysis(normalize_space(cleaned_for_analysis)[:12000], role_target, target_skills)
            section_reviews = llm_provider.llm_section_reviews(cleaned_for_analysis[:12000]) or evaluator.fallback_section_reviews(
                cleaned_for_analysis
            )

            issues: list[str] = []
            tips: list[str] = []
            inferred_roles: list[str] = []
            section_skills: list[str] = []
            bs_factors: list[int] = []
            for review in section_reviews:
                issues.extend([str(i) for i in (review.get("issues") or []) if str(i).strip()])
                tips.extend([str(i) for i in (review.get("tips") or []) if str(i).strip()])
                section_skills.extend([str(i).strip().lower() for i in (review.get("extracted_skills") or []) if str(i).strip()])
                role = str(review.get("inferred_role", "")).strip()
                if role:
                    inferred_roles.append(role)
                try:
                    bs = int(review.get("bs_factor", 0))
                    if 1 <= bs <= 10:
                        bs_factors.append(bs)
                except Exception:
                    pass

            merged_skills = sorted(set(skills + section_skills))
            merged_gap = evaluator.compute_skill_gap(merged_skills, target_skills)
            avg_bs = (sum(bs_factors) / len(bs_factors)) if bs_factors else 5.0
            issue_penalty = min(len(issues), 12) * 2
            gap_penalty = min(len(merged_gap), 10) * 5
            bs_penalty = int(avg_bs * 4)
            computed_score = max(35, min(95, deterministic_base_score - issue_penalty - gap_penalty - bs_penalty + 12))

            llm_score_raw = semantic.get("score", computed_score)
            try:
                llm_score = int(llm_score_raw)
            except Exception:
                llm_score = computed_score
            final_score = max(35, min(95, int((computed_score * 0.6) + (llm_score * 0.4))))

            response = {
                "skills": merged_skills,
                "projects": projects,
                "experience_level": semantic.get("experience_level", deterministic["experience_level"]),
                "strengths": semantic.get("strengths", deterministic["strengths"])[:3],
                "weaknesses": (semantic.get("weaknesses", []) or issues or deterministic["weaknesses"])[:5],
                "recommended_roles": (
                    semantic.get("recommended_roles", [])
                    or inferred_roles
                    or deterministic["recommended_roles"]
                )[:5],
                "skill_gap": (semantic.get("skill_gap", []) or merged_gap)[:10],
                "score": final_score,
                "section_reviews": section_reviews[:5],
            }
            response["detailed_review"] = self._build_detailed_review(response["section_reviews"], response["score"])
            return response
        except Exception:
            return deterministic


analyzer = ResumeAnalyzer()
