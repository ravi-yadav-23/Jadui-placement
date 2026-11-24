"""Job description -> JobRequirements, with the LLM's output checked against the JD text."""

import re

from app.llm.client import LLMClient
from app.resume.pipeline.structure import normalize
from app.resume.pipeline.taxonomy import find_skills, normalize_skill
from app.resume.schemas import JdDraft, JobRequirements, Requirement


def build_requirements(draft: JdDraft, jd_text: str) -> JobRequirements:
    source = normalize(jd_text)
    requirements = []
    for i, req in enumerate(draft.requirements):
        # Canonical skill names, plus any taxonomy skills the LLM forgot to list for this requirement.
        skills = {normalize_skill(s) for s in req.skills} | find_skills(req.text)
        requirements.append(Requirement(id=f"r{i}", text=req.text, kind=req.kind, skills=sorted(skills)))

    # A knockout is only kept if its value really appears in the JD: a wrong "CGPA 8+" would
    # wrongly tell the candidate they are ineligible.
    knockouts = [k for k in draft.knockouts if normalize(k.value) in source]

    min_years = draft.min_years
    if min_years is not None and not re.search(rf"(?<!\d){min_years:g}\s*\+?\s*(?:years?|yrs?)", jd_text, re.I):
        min_years = None

    return JobRequirements(
        title=draft.title,
        company=draft.company,
        seniority=draft.seniority,
        min_years=min_years,
        requirements=requirements,
        knockouts=knockouts,
        keywords=draft.keywords[:15],
        responsibilities=draft.responsibilities[:10],
    )


def parse_jd(llm: LLMClient, jd_text: str) -> JobRequirements:
    draft = llm.structured("jd_parse", JdDraft, {"jd_text": jd_text})
    return build_requirements(draft, jd_text)
