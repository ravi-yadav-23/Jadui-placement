import re
from .utils import normalize_space
from .constants import COMMON_SKILLS

class SectionParser:
    def extract_all_sections(self, resume_text: str) -> dict[str, str]:
        sections = {
            "personal_summary": self.extract_section(
                resume_text,
                [r"^personal details", r"^contact", r"^professional summary", r"^summary", r"^profile"],
            ),
            "technical_skills": self.extract_section(resume_text, [r"^technical skills", r"^skills", r"^tech stack"]),
            "experience": self.extract_section(resume_text, [r"^experience", r"^work experience", r"^employment"]),
            "projects": self.extract_section(resume_text, [r"^projects", r"^project"]),
            "leadership_achievements": self.extract_section(
                resume_text,
                [r"^leadership", r"^achievements", r"^leadership\s*&\s*achievements", r"^positions of responsibility"],
            ),
        }
        for key, value in list(sections.items()):
            if value:
                continue
            sections[key] = self.infer_section_without_heading(resume_text, key)
        return sections

    def infer_section_without_heading(self, resume_text: str, section: str) -> str:
        lines = [ln.strip() for ln in (resume_text or "").splitlines() if ln.strip()]
        low_lines = [ln.lower() for ln in lines]
        if not lines:
            return ""

        if section == "personal_summary":
            # Use top block before clear experience/project timeline markers.
            stop_words = ("experience", "work experience", "projects", "skills", "education")
            block: list[str] = []
            for line in lines[:18]:
                if any(sw in line.lower() for sw in stop_words):
                    break
                block.append(line)
            return normalize_space("\n".join(block[:6]))

        if section == "technical_skills":
            skill_lines = [
                lines[i]
                for i, low in enumerate(low_lines)
                if "," in low and sum(1 for s in COMMON_SKILLS if s in low) >= 2
            ]
            return normalize_space("\n".join(skill_lines[:4]))

        if section == "experience":
            exp_tokens = ("intern", "developer", "engineer", "company", "present", "month", "year")
            exp_lines = [lines[i] for i, low in enumerate(low_lines) if any(t in low for t in exp_tokens)]
            return normalize_space("\n".join(exp_lines[:8]))

        if section == "projects":
            proj_tokens = ("project", "built", "developed", "implemented", "deployed", "github")
            proj_lines = [lines[i] for i, low in enumerate(low_lines) if any(t in low for t in proj_tokens)]
            return normalize_space("\n".join(proj_lines[:8]))

        if section == "leadership_achievements":
            leader_tokens = ("lead", "mentored", "organized", "hackathon", "winner", "achievement", "community")
            leader_lines = [lines[i] for i, low in enumerate(low_lines) if any(t in low for t in leader_tokens)]
            return normalize_space("\n".join(leader_lines[:6]))

        return ""

    def extract_section(self, text: str, heading_patterns: list[str]) -> str:
        lines = text.splitlines()
        if not lines:
            return ""
        starts: list[int] = []
        for idx, line in enumerate(lines):
            low = line.strip().lower()
            if any(re.search(pat, low) for pat in heading_patterns):
                starts.append(idx)
        if not starts:
            return ""
        start = starts[0] + 1
        end = len(lines)
        heading_any = re.compile(
            r"^\s*(summary|professional summary|skills|technical skills|experience|work experience|projects|project|leadership|achievements|education|certifications?)\s*:?\s*$",
            re.IGNORECASE,
        )
        for idx in range(start, len(lines)):
            if heading_any.search(lines[idx].strip()):
                end = idx
                break
        return normalize_space("\n".join(lines[start:end]).strip())

    def extract_skills(self, text: str) -> list[str]:
        norm = text.lower()
        found = []
        for s in COMMON_SKILLS:
            pattern = r'(?<![a-zA-Z0-9])' + re.escape(s) + r'(?![a-zA-Z0-9])'
            if re.search(pattern, norm):
                found.append(s)
        return sorted(found)

    def extract_projects(self, text: str) -> list[str]:
        lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
        keywords = ("project", "built", "developed", "implemented", "designed")
        projects = [line for line in lines if any(k in line.lower() for k in keywords)]
        return projects[:5]

    def infer_experience_level(self, text: str) -> str:
        norm = text.lower()
        match = re.search(r"(\d+)\+?\s+years?", norm)
        years = int(match.group(1)) if match else 0
        if years >= 10:
            return "lead"
        if years >= 6:
            return "senior"
        if years >= 3:
            return "mid"
        if years >= 1:
            return "junior"
        return "entry"

section_parser = SectionParser()
