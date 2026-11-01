import re
from typing import Any
from .constants import BANNED_SOFT_PHRASES, SECTION_LABELS, SECTION_KEYS
from .section_parser import section_parser

class Evaluator:
    def sanitize_tone_line(self, text: str) -> str:
        line = str(text or "").strip()
        low = line.lower()
        if any(phrase in low for phrase in BANNED_SOFT_PHRASES):
            return ""
        # Keep lines short and sharp.
        if len(line) > 220:
            line = line[:220].rstrip() + "."
        return line

    def sanitize_review_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(payload or {})
        for key in ("issues", "justification", "tips"):
            vals = cleaned.get(key) or []
            sanitized = [self.sanitize_tone_line(v) for v in vals]
            cleaned[key] = [v for v in sanitized if v][:8]
        cleaned["improved_block"] = self.sanitize_tone_line(cleaned.get("improved_block", ""))
        return cleaned

    def compute_skill_gap(self, extracted_skills: list[str], target_skills: list[str]) -> list[str]:
        if not target_skills:
            return []
        extracted = {s.lower() for s in extracted_skills}
        return [s for s in target_skills if s.lower() not in extracted]

    def deterministic_quality_audit(self, text: str) -> dict[str, Any]:
        norm = text.lower()
        issues: list[str] = []
        tips: list[str] = []

        if "linkedin.com" not in norm:
            issues.append("LinkedIn URL missing from personal details.")
            tips.append("Add a clickable LinkedIn URL in the header.")
        if "github.com" not in norm:
            issues.append("GitHub URL missing from personal details.")
            tips.append("Add a clickable GitHub profile URL.")
        if "summary" not in norm and "professional summary" not in norm:
            issues.append("Professional summary section is missing or unclear.")
            tips.append("Add a 2-3 line summary with target role and backend strengths.")

        weak_phrases = ["passionate", "hardworking", "worked on", "helped with", "responsible for"]
        weak_hits = [phrase for phrase in weak_phrases if phrase in norm]
        if weak_hits:
            issues.append("Generic/weak phrasing detected: " + ", ".join(weak_hits[:3]))
            tips.append("Replace generic phrases with action + technical impact statements.")

        section_keywords = ["skills", "experience", "projects"]
        missing_sections = [sec for sec in section_keywords if sec not in norm]
        if missing_sections:
            issues.append("Important sections appear missing: " + ", ".join(missing_sections))
            tips.append("Ensure Skills, Experience, and Projects headings are clearly present.")

        if len(text.split()) < 120:
            issues.append("Resume content appears too short for a competitive technical profile.")
            tips.append("Add stronger project depth, APIs/system design contributions, and measurable outcomes.")

        # Conservative score model that avoids unrealistically perfect scores.
        score = 88 - (len(issues) * 7)
        score = max(40, min(88, score))
        return {"issues": issues, "tips": tips[:3], "score": score}

    def deterministic_section_review(self, section: str, section_text: str, full_text: str) -> dict[str, Any]:
        text = (section_text or "").strip()
        full = (full_text or "").lower()
        low = text.lower()
        issues: list[str] = []
        tips: list[str] = []
        improved_block = ""
        extracted_skills: list[str] = []
        inferred_role = ""
        exp_level = section_parser.infer_experience_level(full_text)
        confidence = 88

        if section == "personal_summary":
            if not text:
                issues.append("Personal details/professional summary section is missing.")
                confidence -= 35
            if "linkedin.com" not in full:
                issues.append("LinkedIn URL missing in contact header.")
                confidence -= 8
            if "github.com" not in full:
                issues.append("GitHub URL missing in contact header.")
                confidence -= 8
            weak_words = [w for w in ("passionate", "hardworking", "enthusiastic") if w in low]
            if weak_words:
                issues.append("Summary uses weak claims: " + ", ".join(weak_words))
                confidence -= 12
            tips = [
                "Keep summary to 2-3 lines with role-first positioning.",
                "Add clickable LinkedIn and GitHub links in one clean line.",
                "Replace generic adjectives with backend/API strengths.",
            ]
            improved_block = (
                "Full Stack Developer focused on backend APIs, scalable web systems, and SQL-driven applications. "
                "Builds production-grade features across React/Next.js and Python/Node backends with measurable delivery outcomes."
            )

        elif section == "technical_skills":
            extracted_skills = section_parser.extract_skills(text or full_text)
            if not text:
                issues.append("Technical Skills section is missing.")
                confidence -= 30
            if len(extracted_skills) < 5:
                issues.append("Skill depth appears limited for software engineering screening.")
                confidence -= 14
            if len(extracted_skills) > 16:
                issues.append("Skill list is overloaded and may reduce credibility.")
                confidence -= 10
            tips = [
                "Group skills by Languages, Frontend, Backend, Databases, Tools.",
                "Remove technologies you cannot defend in interviews.",
                "Keep stack aligned to target role requirements.",
            ]
            improved_block = (
                "Languages: JavaScript, TypeScript, Python, SQL | "
                "Frontend: React, Next.js | Backend: Node.js, FastAPI | "
                "Databases: PostgreSQL, MySQL, MongoDB | Tools: Git, Docker"
            )

        elif section == "experience":
            if not text:
                issues.append("Experience section is missing.")
                confidence -= 35
            weak_hits = [p for p in ("worked on", "helped with", "responsible for", "collaborated") if p in low]
            if weak_hits:
                issues.append("Experience bullets use weak phrasing: " + ", ".join(weak_hits[:3]))
                confidence -= 12
            if not re.search(r"\d+%|\d+\s*(ms|sec|users|requests|x)", low):
                issues.append("Experience bullets lack measurable impact signals.")
                confidence -= 10
            tips = [
                "Rewrite bullets in Problem -> Action -> Result format.",
                "Start each bullet with strong engineering verbs.",
                "Add measurable impact only where factual and defensible.",
            ]
            improved_block = (
                "- Reduced API response latency by optimizing query paths and caching critical endpoints.\n"
                "- Built and deployed backend services for auth, data validation, and analytics workflows."
            )

        elif section == "projects":
            if not text:
                issues.append("Projects section is missing.")
                confidence -= 35
            if "api" not in low:
                issues.append("Project write-up lacks explicit API/backend implementation details.")
                confidence -= 12
            if all(k not in low for k in ("postgres", "mysql", "mongodb", "database")):
                issues.append("Database design/usage is not clearly mentioned.")
                confidence -= 10
            tips = [
                "Lead with strongest technically deep project first.",
                "State architecture choices: API, DB, auth, caching, deployment.",
                "Describe how features were built, not just what they do.",
            ]
            improved_block = (
                "- Designed REST APIs with role-based auth and PostgreSQL schema for core workflows.\n"
                "- Implemented backend validation and async processing to improve reliability under load."
            )

        elif section == "leadership_achievements":
            if not text:
                issues.append("Leadership & Achievements section is missing.")
                confidence -= 25
            if len(text.split()) < 20:
                issues.append("Leadership section is too thin to influence shortlist decisions.")
                confidence -= 8
            if any(k in low for k in ("helped others", "shared knowledge")):
                issues.append("Leadership claims are generic and not tied to scale or impact.")
                confidence -= 12
            tips = [
                "Keep only verifiable achievements with clear impact.",
                "Prioritize technical leadership over generic statements.",
                "Put strongest achievement first with scale/context.",
            ]
            improved_block = (
                "- Led technical delivery for multi-feature release with clear ownership boundaries.\n"
                "- Drove measurable process improvement through code quality and review standards."
            )

        bs_factor = min(10, max(2, 3 + len(issues)))
        return self.sanitize_review_payload(
            {
                "section": section,
                "bs_factor": bs_factor,
                "issues": issues or [f"{SECTION_LABELS.get(section, section)} needs stronger technical clarity."],
                "improved_block": improved_block,
                "justification": [f"Focused on recruiter signal quality for {SECTION_LABELS.get(section, section)}."],
                "tips": tips,
                "extracted_skills": extracted_skills[:15],
                "inferred_role": inferred_role,
                "experience_level": exp_level,
                "confidence": max(20, min(95, confidence)),
            }
        )

    def fallback_section_reviews(self, text: str) -> list[dict[str, Any]]:
        sections = section_parser.extract_all_sections(text)
        reviews = [
            self.deterministic_section_review(section, sections.get(section, ""), text)
            for section in SECTION_KEYS
        ]
        return reviews

evaluator = Evaluator()
