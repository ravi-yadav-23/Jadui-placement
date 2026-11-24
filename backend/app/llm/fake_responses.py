"""Canned LLM answers used when LLM_PROVIDER=fake (unit tests and the Playwright E2E run).

They are realistic enough for the UI to render every section, and deterministic,
so E2E assertions never flake. Real behaviour is measured by the eval suite instead.
"""

import json
import re

from app.resume.pipeline.sections import alias_map, normalize_heading


def default_responder(prompt_name: str, prompt: str) -> dict:
    handler = _HANDLERS.get(prompt_name)
    if handler is None:
        raise KeyError(f"No fake response registered for prompt '{prompt_name}'")
    return handler(prompt)


def _quoted_block(prompt: str) -> str:
    """The input text sits between the first pair of triple quotes in every prompt."""
    parts = prompt.split('"""')
    return parts[1].strip() if len(parts) >= 3 else ""


def _fake_structure(prompt: str) -> dict:
    """Split by known headings; first line of a block = entry title, the rest = bullets."""
    blocks: dict[str, list[str]] = {}
    current = None
    for line in _quoted_block(prompt).split("\n"):
        section = alias_map().get(normalize_heading(line))
        if section:
            current = section
            blocks[current] = []
        elif current and line.strip():
            blocks[current].append(line.strip())

    def entry(lines: list[str]) -> list[dict]:
        if not lines:
            return []
        title, *rest = lines
        return [{"title": title, "bullets": [b for b in rest if len(b.split()) > 3]}]

    education = []
    for line in blocks.get("education", [])[:1]:
        year = re.findall(r"\b20\d{2}\b", line)
        cgpa = re.search(r"CGPA\s*([\d.]+)", line)
        education.append({"institution": line.split(",")[1].strip() if "," in line else line,
                          "grad_year": int(year[-1]) if year else None,
                          "cgpa": float(cgpa.group(1)) if cgpa else None, "cgpa_scale": 10 if cgpa else None})
    skills = [s.strip() for line in blocks.get("skills", []) for s in line.split(",") if s.strip()]
    return {
        "education": education,
        "experience": entry(blocks.get("experience", [])),
        "projects": entry(blocks.get("projects", [])),
        "skills": skills,
        "achievements": blocks.get("achievements", []),
    }


def _fake_review(prompt: str) -> dict:
    """Bullets with a number rate higher; bullets without one get a [X] rewrite and a coach question."""
    ratings = []
    for item in json.loads(_quoted_block(prompt)):
        has_metric = "no_metric" not in item["rule_issues"]
        ratings.append({
            "bullet_id": item["bullet_id"],
            "specificity": 4 if has_metric else 3,
            "technical_depth": 3,
            "outcome": 4 if has_metric else 2,
            "issues": [] if has_metric else ["unclear_outcome"],
            "rewrite": None if has_metric else item["text"].rstrip(".") + ", reducing manual effort by [X]%",
            "coach_questions": [] if has_metric else ["What measurable result did this have?"],
        })
    return {
        "bullets": ratings,
        "strengths": ["Relevant backend stack shown in real projects."],
        "top_actions": ["Add a measurable result to every bullet that lacks one."],
    }


def _fake_jd_parse(prompt: str) -> dict:
    """Bullet lines are requirements; lines after a 'nice to have' style heading are optional."""
    from app.resume.pipeline.taxonomy import find_skills

    lines = [ln.strip() for ln in _quoted_block(prompt).split("\n") if ln.strip()]
    requirements, knockouts, kind = [], [], "must"
    for line in lines:
        low = line.lower()
        if any(word in low for word in ("nice to have", "preferred", "bonus")):
            kind = "nice"
        elif "eligibility" in low:
            kind = "eligibility"
        elif line.startswith("-"):
            text = line.lstrip("- ").strip()
            if kind == "eligibility":
                cgpa = re.search(r"CGPA [\d.]+", text)
                batch = re.search(r"20\d\d batch", text)
                if cgpa:
                    knockouts.append({"type": "cgpa", "value": cgpa.group(0)})
                if batch:
                    knockouts.append({"type": "grad_year", "value": batch.group(0)})
            else:
                requirements.append({"text": text, "kind": kind, "skills": sorted(find_skills(text))})
    if "on-site" in prompt.lower():
        location = re.search(r"Location: ([^\n]+)", prompt)
        if location:
            knockouts.append({"type": "location", "value": location.group(1).strip()})
    return {
        "title": lines[0].split(" - ")[0] if lines else "Unknown role",
        "company": lines[0].split(" - ")[1] if lines and " - " in lines[0] else None,
        "seniority": "intern" if "intern" in prompt.lower() else "unknown",
        "requirements": requirements,
        "knockouts": knockouts,
        "keywords": sorted({s for r in requirements for s in r["skills"]}),
        "responsibilities": [],
    }


_HANDLERS = {
    "resume_structure": _fake_structure,
    "resume_review": _fake_review,
    "jd_parse": _fake_jd_parse,
}
