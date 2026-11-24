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


# ---------- JD match ----------
# Must-haves 45 + Nice-to-haves 15 + Evidence depth 15 + Experience fit 10 + Role alignment 5 + Knockouts 10

STATUS_WEIGHT = {"strong": 1.0, "partial": 0.5, "listed_only": 0.5, "missing": 0.0}

TIERS = [  # (minimum score, tier, honest advice)
    (80, "strong", "Strong fit. Apply, and use the tailoring suggestions for your top bullets."),
    (60, "good", "Good fit. Apply after closing the easy gaps below."),
    (40, "stretch", "Stretch. Apply with your base resume; don't stretch claims. The gaps are saved to your plan."),
    (0, "not_a_fit", "Not a fit yet. Don't stretch your resume for this one; focus on the missing must-haves."),
]


def coverage(matches, kind: str, maximum: int, label: str) -> SubScore:
    items = [m for m in matches if m.kind == kind]
    if not items:
        return _sub(f"{kind}_coverage", label, maximum, maximum, f"The JD lists no {label.lower()}.")
    met = sum(STATUS_WEIGHT[m.status] for m in items)
    return _sub(f"{kind}_coverage", label, maximum * met / len(items), maximum,
                f"{met:g} of {len(items)} covered (strong = 1, partial or only listed = 0.5).")


def evidence_depth(matches) -> SubScore:
    musts = [m for m in matches if m.kind == "must" and m.status != "missing"]
    if not musts:
        return _sub("evidence_depth", "Evidence depth", 0, 15, "No must-have requirement is covered yet.")
    proven = sum(m.status == "strong" for m in musts)
    return _sub("evidence_depth", "Evidence depth", 15 * proven / len(musts), 15,
                f"{proven} of {len(musts)} covered must-haves are proven by a bullet, not just listed.")


def experience_fit(seniority: str, min_years: float | None, is_student: bool) -> SubScore:
    if min_years is None and seniority in ("intern", "entry", "unknown"):
        return _sub("experience_fit", "Experience fit", 10, 10, "No experience requirement beyond entry level.")
    if seniority in ("mid", "senior") or (min_years or 0) >= 2:
        if is_student:
            return _sub("experience_fit", "Experience fit", 0, 10,
                        f"The role asks for {min_years or seniority} experience; your resume reads as a student.")
        return _sub("experience_fit", "Experience fit", 5, 10, "Years of experience couldn't be verified.")
    return _sub("experience_fit", "Experience fit", 10, 10, "Experience requirement looks achievable.")


def knockout_points(knockouts) -> SubScore:
    if any(k.status == "conflict" for k in knockouts):
        return _sub("knockouts", "Knockouts", 0, 10, "At least one eligibility rule isn't met (see the warning).")
    if any(k.status == "unknown" for k in knockouts):
        return _sub("knockouts", "Knockouts", 5, 10, "Some eligibility rules couldn't be checked from the resume.")
    return _sub("knockouts", "Knockouts", 10, 10, "No eligibility conflicts found.")


def jd_score(matches, knockouts, role_alignment: int, seniority: str, min_years, is_student: bool):
    subs = [
        coverage(matches, "must", 45, "Must-haves"),
        coverage(matches, "nice", 15, "Nice-to-haves"),
        evidence_depth(matches),
        experience_fit(seniority, min_years, is_student),
        _sub("role_alignment", "Role alignment", role_alignment, 5,
             f"AI rating {role_alignment}/5 of how well your overall direction fits this role."),
        knockout_points(knockouts),
    ]
    total = round(sum(s.score for s in subs))
    _, tier, message = next(t for t in TIERS if total >= t[0])
    return total, tier, message, subs


def general_score(checks, bullets, profile, contacts, unsupported_skills: int) -> tuple[int, list[SubScore]]:
    subs = [
        parse_health(checks),
        impact(bullets),
        clarity(bullets),
        completeness(profile, contacts),
        substance(bullets, unsupported_skills),
    ]
    return round(sum(s.score for s in subs)), subs
