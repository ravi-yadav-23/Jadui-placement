"""The two places the planner uses an LLM: the roadmap explanation and project ideas (plan §7).

Both are checked by code before they are shown, and both have a template fallback, so a plan never depends on
the LLM:
  * summary  - no digits allowed (hours and dates come from code); no mention of subjects not in the plan;
               phase names must match the scheduler's phases
  * projects - technologies must come from your stack, your gaps or the role's list; no duplicates of your
               resume projects
"""

from __future__ import annotations

import json
import logging
import re

from rapidfuzz import fuzz

from app.planner.schemas import PlannerProfile, ProjectIdea, ProjectsDraft, RoadmapSummary, SummaryDraft

log = logging.getLogger(__name__)

SUBJECT_WORDS = {"aptitude": ["aptitude"], "hld": ["high-level design", "hld"],
                 "lld": ["low-level design", "lld", "machine coding"]}
ROLE_TECH = {
    "sde": ["Python", "Java", "PostgreSQL", "Redis", "Docker", "REST APIs", "React", "Git"],
    "backend": ["Python", "FastAPI", "Node.js", "Java", "Spring Boot", "PostgreSQL", "Redis", "Docker", "Celery",
                "REST APIs", "Kafka"],
    "frontend": ["JavaScript", "TypeScript", "React", "Next.js", "Tailwind CSS", "Jest", "Playwright"],
    "fullstack": ["TypeScript", "React", "Next.js", "Node.js", "PostgreSQL", "Docker", "REST APIs"],
    "data": ["Python", "Pandas", "SQL", "scikit-learn", "PostgreSQL", "Airflow", "Streamlit"],
}
LEVEL_WORDS = {"entry": "an entry-level role", "mid": "a mid-level (1-3 years) role",
               "senior": "a senior (3-5 years) role"}
ROLE_WORDS = {"sde": "software engineering", "backend": "backend engineering", "frontend": "frontend engineering",
              "fullstack": "full-stack engineering", "data": "data / ML engineering"}


# ---------- Summary ----------

def summary_facts(profile: PlannerProfile, subjects: list[str], labels: dict[str, str], phases: list[dict],
                  cut: list[str]) -> dict:
    return {
        "level": LEVEL_WORDS[profile.level], "target_role": ROLE_WORDS[profile.target_role],
        "company_types": profile.company_types, "status": profile.status, "year": profile.year,
        "subjects": [labels[s] for s in subjects], "phases": phases, "cut": cut[:6],
    }


def template_summary(facts: dict) -> RoadmapSummary:
    focus = ", ".join(facts["subjects"][:4])
    overview = (f"This plan prepares you for {facts['level']} in {facts['target_role']}. "
                f"Most of your time goes to {focus}, with spaced reviews and mock-interview checkpoints so you "
                f"remember what you learn.")
    if facts["cut"]:
        overview += " Some lower-priority topics did not fit in your time; see the note below."
    texts = {
        "Foundation": "Basics and prerequisites first, so later topics have something to build on.",
        "Core": "The main topics of every subject, interleaved across the week.",
        "Advanced": "Harder patterns, design problems and finishing your project.",
        "Final revision and mocks": "No new topics: timed practice, revision and full mock interviews.",
    }
    return RoadmapSummary(overview=overview, source="template",
                          phases=[{"name": p["name"], "text": texts.get(p["name"], "")} for p in facts["phases"]])


def ai_summary(llm, facts: dict, subjects_in_plan: set[str]) -> RoadmapSummary:
    draft = llm.structured("planner_summary", SummaryDraft, {"facts_json": json.dumps(facts, indent=1)},
                           temperature=0.3)
    phase_names = [p["name"] for p in facts["phases"]]
    texts = {p.name: p.text.strip() for p in draft.phases if p.name in phase_names}
    all_text = " ".join([draft.overview, *texts.values()])
    if re.search(r"\d", all_text):
        raise ValueError("summary contains numbers")
    lower = all_text.lower()
    for subject, words in SUBJECT_WORDS.items():
        if subject not in subjects_in_plan and any(w in lower for w in words):
            raise ValueError(f"summary mentions {subject}, which is not in the plan")
    return RoadmapSummary(overview=draft.overview.strip(), source="ai",
                          phases=[{"name": n, "text": texts.get(n, "")} for n in phase_names])


# ---------- Projects ----------

def project_inputs(profile: PlannerProfile, resume_projects: list[str], resume_skills: list[str],
                   gaps: list[str]) -> dict:
    allowed = list(dict.fromkeys([*profile.stack, *resume_skills, *gaps, *ROLE_TECH[profile.target_role]]))
    return {"target_role": ROLE_WORDS[profile.target_role], "level": LEVEL_WORDS[profile.level],
            "stack": profile.stack, "existing_projects": resume_projects, "gaps": gaps, "allowed_tech": allowed}


def ai_projects(llm, candidate: dict, count: int = 3) -> list[ProjectIdea]:
    draft = llm.structured("planner_projects", ProjectsDraft,
                           {"candidate_json": json.dumps(candidate, indent=1), "count": str(count)}, temperature=0.5)
    allowed = {t.lower(): t for t in candidate["allowed_tech"]}
    ideas = []
    for idea in draft.projects[:count]:
        tech = [allowed[t.lower()] for t in idea.tech if t.lower() in allowed]
        duplicate = any(fuzz.ratio(idea.title.lower(), p.lower()) >= 80 for p in candidate["existing_projects"])
        if len(tech) >= 2 and not duplicate and len(idea.milestones) >= 3:
            ideas.append(idea.model_copy(update={"tech": tech[:6], "milestones": idea.milestones[:6]}))
    return ideas
