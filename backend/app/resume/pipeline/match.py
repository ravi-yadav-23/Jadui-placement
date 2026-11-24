"""JD match: for every requirement, find the bullet that proves it, or say it's missing.

  1. Rules first: if every skill a requirement names appears in some grounded bullet
     (counting implied skills, e.g. FastAPI -> Python), it's "strong", and we cite that bullet.
  2. One LLM call judges the remaining requirements (including non-skill ones like
     "built production APIs"), rates role alignment, and suggests tailored rewrites.
  3. We validate the LLM: cited bullet IDs must exist; "strong" without valid evidence is
     downgraded. Listed-but-unproven skills become "listed_only".
"""

import json
from dataclasses import dataclass

from app.llm.client import LLMClient
from app.resume.pipeline.guard import guard_rewrite
from app.resume.pipeline.taxonomy import find_skills, normalize_skill, with_implied
from app.resume.schemas import (
    Bullet,
    Evidence,
    JobRequirements,
    MatchDraft,
    Requirement,
    RequirementJudgment,
    RequirementMatch,
    ResumeProfile,
    TailoredBullet,
)

MAX_TAILORED = 5


@dataclass
class BulletRef:
    bullet: Bullet
    stack: set[str]   # technologies listed for the bullet's job/project
    skills: set[str]  # skills this bullet demonstrates (including implied ones)


@dataclass
class MatchOutput:
    requirements: list[RequirementMatch]
    role_alignment: int
    tailored: list[TailoredBullet]
    summary: str | None


def bullet_refs(profile: ResumeProfile) -> list[BulletRef]:
    refs = []
    for entry in profile.experience + profile.projects:
        stack = {normalize_skill(t) for t in entry.tech}
        refs += [BulletRef(b, stack, with_implied(find_skills(b.text))) for b in entry.bullets if b.grounded]
    refs += [BulletRef(b, set(), with_implied(find_skills(b.text))) for b in profile.achievements if b.grounded]
    return refs


def listed_skills(profile: ResumeProfile) -> set[str]:
    """Skills the candidate claims (skills section + project/job stacks), without bullet proof."""
    stacks = {normalize_skill(t) for e in profile.experience + profile.projects for t in e.tech}
    return with_implied({normalize_skill(s) for s in profile.skills} | stacks)


def _evidence(refs: list[BulletRef]) -> list[Evidence]:
    unique = {r.bullet.id: r for r in refs}
    return [Evidence(bullet_id=r.bullet.id, text=r.bullet.text) for r in unique.values()]


def rule_match(req: Requirement, refs: list[BulletRef]) -> RequirementMatch | None:
    """Strong match decided by code alone, or None when the LLM has to judge."""
    if not req.skills:
        return None
    proof = []
    for skill in req.skills:
        hit = next((r for r in refs if skill in r.skills), None)
        if hit is None:
            return None
        proof.append(hit)
    return RequirementMatch(requirement_id=req.id, text=req.text, kind=req.kind, skills=req.skills,
                            status="strong", evidence=_evidence(proof), decided_by="rules",
                            reason=f"Shown in your bullets: {', '.join(req.skills)}.")


def validate_judgment(req: Requirement, judgment: RequirementJudgment | None, refs_by_id: dict[str, BulletRef],
                      listed: set[str]) -> RequirementMatch:
    status = judgment.status if judgment else "missing"
    reason = judgment.reason if judgment else "Not assessed."
    proof = [refs_by_id[i] for i in (judgment.evidence_bullet_ids if judgment else []) if i in refs_by_id]
    if status != "missing" and not proof:
        status, reason = "missing", "No bullet supports this."
    if status == "missing" and any(skill in listed for skill in req.skills):
        status, reason = "listed_only", "Listed on your resume, but no bullet shows you using it."
    return RequirementMatch(requirement_id=req.id, text=req.text, kind=req.kind, skills=req.skills, status=status,
                            evidence=_evidence(proof), reason=reason, decided_by="ai")


def _fact_text(profile: ResumeProfile) -> str:
    """Everything the candidate states: the 'original' a summary suggestion must stay within."""
    parts = [profile.summary or "", profile.headline or "", " ".join(profile.skills)]
    parts += [b.text for b in profile.all_bullets() if b.grounded]
    parts += [f"{e.title} {e.org or ''} {' '.join(e.tech)}" for e in profile.experience + profile.projects]
    return " ".join(parts)


def match_profile(llm: LLMClient, profile: ResumeProfile, jd: JobRequirements) -> MatchOutput:
    refs = bullet_refs(profile)
    refs_by_id = {r.bullet.id: r for r in refs}
    listed = listed_skills(profile)

    decided = {req.id: rule_match(req, refs) for req in jd.requirements}
    pending = [req for req in jd.requirements if decided[req.id] is None]

    draft = llm.structured("jd_match", MatchDraft, {
        "jd_title": jd.title,
        "requirements_json": json.dumps([{"requirement_id": r.id, "text": r.text, "kind": r.kind}
                                         for r in pending], indent=1),
        "bullets_json": json.dumps([{"bullet_id": r.bullet.id, "text": r.bullet.text} for r in refs], indent=1),
        "skills": ", ".join(profile.skills) or "(none listed)",
    })
    judgments = {j.requirement_id: j for j in draft.judgments}

    matches = [decided[req.id] or validate_judgment(req, judgments.get(req.id), refs_by_id, listed)
               for req in jd.requirements]

    tailored = []
    for item in draft.tailored_bullets[:MAX_TAILORED]:
        ref = refs_by_id.get(item.bullet_id)
        if ref is None:
            continue
        guarded = guard_rewrite(ref.bullet.text, item.rewrite, allowed_tech=ref.stack)
        if guarded.text and guarded.text != ref.bullet.text:
            tailored.append(TailoredBullet(bullet_id=ref.bullet.id, original=ref.bullet.text, rewrite=guarded.text,
                                           keywords=item.keywords, guard_notes=guarded.notes))

    summary = guard_rewrite(_fact_text(profile), draft.summary_suggestion, allowed_tech=listed).text
    return MatchOutput(matches, draft.role_alignment, tailored, summary)


def keyword_coverage(profile: ResumeProfile, jd: JobRequirements) -> tuple[list[str], list[str]]:
    """(keywords you have but no bullet shows, keywords not on the resume at all)."""
    refs = bullet_refs(profile)
    shown = set().union(*(r.skills for r in refs)) if refs else set()
    listed = listed_skills(profile)
    resume_text = _fact_text(profile).lower()
    to_surface, missing = [], []
    for keyword in jd.keywords:
        skill = normalize_skill(keyword)
        if skill in shown:
            continue
        if skill in listed:
            to_surface.append(skill)
        elif keyword.lower() not in resume_text:
            missing.append(keyword)
    return list(dict.fromkeys(to_surface)), list(dict.fromkeys(missing))


def bullet_order(profile: ResumeProfile, jd: JobRequirements, matches: list[RequirementMatch]) -> list[str]:
    """Bullet IDs sorted by relevance to this JD: requirement skills shown + times cited as evidence."""
    wanted = {s for req in jd.requirements for s in req.skills}
    cited: dict[str, int] = {}
    for match in matches:
        for ev in match.evidence:
            cited[ev.bullet_id] = cited.get(ev.bullet_id, 0) + 1
    refs = bullet_refs(profile)
    scored = [(len(r.skills & wanted) + 2 * cited.get(r.bullet.id, 0), i, r.bullet.id) for i, r in enumerate(refs)]
    return [bullet_id for score, _, bullet_id in sorted(scored, key=lambda t: (-t[0], t[1]))]
