"""Canned LLM answers used when LLM_PROVIDER=fake (unit tests and the Playwright E2E run).

They are realistic enough for the UI to render every section, and deterministic,
so E2E assertions never flake. Real behaviour is measured by the eval suite instead.
"""

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


_HANDLERS = {
    "resume_structure": _fake_structure,
}
