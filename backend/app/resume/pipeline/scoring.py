"""Score formulas. Every number shown in the UI comes from here, with its explanation.

General score (0-100) = Parse health (20) + Impact (25) + Clarity (15) + Completeness (15) + Substance (25)
75 of the 100 points are deterministic; only "Substance" uses the LLM's 1-5 ratings.
"""

from app.resume.schemas import BulletFeedback, Check, Contacts, ResumeProfile, SubScore

CLARITY_ISSUES = {"length", "pronoun", "passive", "buzzword", "vague"}
MAX_UNSUPPORTED_PENALTY = 6


def _sub(key: str, label: str, score: float, maximum: int, explanation: str) -> SubScore:
    return SubScore(key=key, label=label, score=round(max(0.0, min(score, maximum)), 1), max=maximum,
                    explanation=explanation)


def parse_health(checks: list[Check]) -> SubScore:
    fails = sum(c.status == "fail" for c in checks)
    warns = sum(c.status == "warn" for c in checks)
    return _sub("parse_health", "Parse health", 20 - 6 * fails - 2 * warns, 20,
                f"20 points minus 6 per failed check ({fails}) and 2 per warning ({warns}).")


def impact(bullets: list[BulletFeedback]) -> SubScore:
    n = len(bullets)
    if n == 0:
        return _sub("impact", "Impact", 0, 25, "No bullet points found to evaluate.")
    quantified = sum("no_metric" not in b.issues for b in bullets)
    strong_start = sum("weak_start" not in b.issues for b in bullets)
    score = 15 * min(1.0, quantified / (0.5 * n)) + 10 * strong_start / n
    return _sub("impact", "Impact", score, 25,
                f"{quantified}/{n} bullets contain a number (full 15 points at half of them) and "
                f"{strong_start}/{n} start with a strong action verb (10 points).")


def clarity(bullets: list[BulletFeedback]) -> SubScore:
    n = len(bullets)
    if n == 0:
        return _sub("clarity", "Clarity", 0, 15, "No bullet points found to evaluate.")
    clean = sum(not (CLARITY_ISSUES & set(b.issues)) for b in bullets)
    return _sub("clarity", "Clarity", 15 * clean / n, 15,
                f"{clean}/{n} bullets are 8-32 words with no pronouns, passive voice, buzzwords or vague words.")


def completeness(profile: ResumeProfile, contacts: Contacts) -> SubScore:
    parts = {
        "email": bool(contacts.email),
        "education": bool(profile.education),
        "skills": bool(profile.skills),
        "experience or projects": bool(profile.experience or profile.projects),
        "LinkedIn + GitHub": bool(contacts.linkedin and contacts.github),
    }
    missing = [name for name, ok in parts.items() if not ok]
    explanation = "3 points each for: " + ", ".join(parts) + "."
    if missing:
        explanation += f" Missing: {', '.join(missing)}."
    return _sub("completeness", "Completeness", 3 * sum(parts.values()), 15, explanation)


def substance(bullets: list[BulletFeedback], unsupported_skills: int) -> SubScore:
    rated = [b for b in bullets if b.specificity is not None]
    if not rated:
        return _sub("substance", "Substance", 0, 25, "No bullets could be rated.")
    average = sum((b.specificity + b.technical_depth + b.outcome) / 15 for b in rated) / len(rated)
    penalty = min(MAX_UNSUPPORTED_PENALTY, 2 * unsupported_skills)
    return _sub("substance", "Substance", 25 * average - penalty, 25,
                f"Average AI rating of specificity, technical depth and outcome ({average * 100:.0f}% of max) "
                f"across {len(rated)} bullets, minus {penalty} for skills listed without evidence.")


def general_score(checks, bullets, profile, contacts, unsupported_skills: int) -> tuple[int, list[SubScore]]:
    subs = [
        parse_health(checks),
        impact(bullets),
        clarity(bullets),
        completeness(profile, contacts),
        substance(bullets, unsupported_skills),
    ]
    return round(sum(s.score for s in subs)), subs
