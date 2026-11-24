"""General review: deterministic lint + ONE LLM call that rates every bullet + the truth guard.

Flow for each grounded bullet:
  lint_bullet()  -> rule issues (no metric, weak start, ...)        [code]
  LLM            -> 1-5 ratings, extra issues, rewrite, questions    [one batched call]
  guard_rewrite()-> rewrite kept, fixed ([X] placeholders) or dropped [code]
"""

import json

from app.llm.client import LLMClient
from app.resume.pipeline.guard import guard_rewrite
from app.resume.pipeline.lint import lint_bullet
from app.resume.pipeline.taxonomy import find_skills
from app.resume.schemas import Bullet, BulletFeedback, ResumeProfile, ReviewDraft

MAX_BULLETS = 40  # keeps one call within a sensible token budget


def _items(profile: ResumeProfile) -> list[tuple[Bullet, str, str | None, set[str]]]:
    """(bullet, section, entry title, technologies allowed in a rewrite of this bullet)."""
    items = []
    for section, entries in (("experience", profile.experience), ("projects", profile.projects)):
        for entry in entries:
            stack = find_skills(" ".join(entry.tech), tech_only=True)
            items += [(b, section, entry.title, stack) for b in entry.bullets if b.grounded]
    items += [(b, "achievements", None, set()) for b in profile.achievements if b.grounded]
    return items[:MAX_BULLETS]


def review_profile(llm: LLMClient, profile: ResumeProfile, target_role: str | None) -> tuple[
        list[BulletFeedback], list[str], list[str]]:
    items = _items(profile)
    rule_issues = {bullet.id: lint_bullet(bullet.text) for bullet, *_ in items}
    payload = [{"bullet_id": b.id, "text": b.text, "rule_issues": rule_issues[b.id]} for b, *_ in items]

    draft = llm.structured("resume_review", ReviewDraft, {
        "bullets_json": json.dumps(payload, indent=1),
        "target_role": target_role or "software engineering",
    })
    ratings = {r.bullet_id: r for r in draft.bullets}  # unknown IDs are simply never looked up

    feedback = []
    for bullet, section, title, stack in items:
        rating = ratings.get(bullet.id)
        guarded = guard_rewrite(bullet.text, rating.rewrite if rating else None, allowed_tech=stack)
        feedback.append(BulletFeedback(
            bullet_id=bullet.id,
            section=section,
            entry_title=title,
            text=bullet.text,
            issues=list(dict.fromkeys(rule_issues[bullet.id] + (rating.issues if rating else []))),
            specificity=rating.specificity if rating else None,
            technical_depth=rating.technical_depth if rating else None,
            outcome=rating.outcome if rating else None,
            rewrite=guarded.text,
            coach_questions=(rating.coach_questions[:2] if rating else []),
            guard_notes=guarded.notes,
        ))
    return feedback, draft.strengths[:3], draft.top_actions[:3]
