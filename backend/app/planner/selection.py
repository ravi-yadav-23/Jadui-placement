"""Which topics go into your plan, and how many minutes each needs (plan §4). Pure functions.

  subject mix   = weights.yaml row for your level + company types (students in year 1-2: their own row)
  topic minutes = (learn minutes + DSA problems × minutes per problem) × knowledge factor
  knowledge factor by self-rating 0..4 = 1.0, 0.8, 0.55, 0.3, 0.15  (4 = a short review only)
  evidence wins: a matching skill gap or an interview score < 60 keeps the factor at 0.55 or more
"""

from __future__ import annotations

from app.planner.curriculum import Topic, load_curriculum, load_weights
from app.planner.schemas import PlannerProfile, PlanTopic

KNOWLEDGE_FACTOR = [1.0, 0.8, 0.55, 0.3, 0.15]
EVIDENCE_FLOOR = 0.55
BASE_MINUTES_PER_PROBLEM = 35
SOLVED_FACTOR = {"0": 1.0, "lt50": 1.0, "50_150": 0.9, "150_300": 0.75, "300_plus": 0.6}
NOT_TAUGHT_FACTOR = 1.2           # BCA / B.Sc / other degrees: CS subjects may not be in the syllabus
CS_SUBJECTS = ["os", "dbms", "cn", "oop"]
RATING_FOR = {"dsa": "dsa", "os": "os", "dbms": "dbms", "cn": "cn", "oop": "oop",
              "lld": "system_design", "hld": "system_design", "aptitude": "aptitude"}
LANGUAGES = {"cpp": "C++", "java": "Java", "python": "Python", "javascript": "JavaScript", "go": "Go"}
CHECKPOINT_MINUTES = 30
GAP_TOPIC_MINUTES = 120
MAX_GAP_TOPICS = 3
PROMOTE = {"nice": "should", "should": "must", "must": "must"}


def subject_weights(profile: PlannerProfile) -> dict[str, float]:
    """Share of study time per subject, as fractions that add up to 1."""
    weights = load_weights()
    if profile.status == "student" and profile.year in (1, 2):
        row = weights["student_year"][profile.year]
    elif profile.level == "entry":
        rows = [weights["entry"][c] for c in profile.company_types]
        row = {s: sum(r.get(s, 0) for r in rows) / len(rows) for s in {s for r in rows for s in r}}
    else:
        row = weights[profile.level]
    order = list(load_curriculum())  # stable subject order
    return {s: row[s] / 100 for s in sorted(row, key=order.index) if row[s] > 0}


def dsa_difficulty(profile: PlannerProfile) -> str:
    if "top_product" in profile.company_types:
        return "top_product"
    if "product" in profile.company_types or profile.level != "entry":
        return "product"
    return "service"


def minutes_per_problem(profile: PlannerProfile) -> float:
    return BASE_MINUTES_PER_PROBLEM * SOLVED_FACTOR[profile.problems_solved]


def project_track(profile: PlannerProfile) -> str:
    return "deepen" if profile.projects >= 2 and profile.projects_deployed else "build"


def matches(topic: Topic, gap: str) -> bool:
    text = gap.lower()
    return topic.title.lower() in text or any(alias in text for alias in topic.aliases)


def select_topics(profile: PlannerProfile, gaps: list[tuple[str, str]],
                  interview_scores: dict[str, int]) -> list[PlanTopic]:
    """`gaps` = [(skill, source)] the user chose to include; `interview_scores` = {"os": 45, ...}."""
    curriculum = load_curriculum()
    weights = subject_weights(profile)
    level, difficulty, per_problem = profile.level, dsa_difficulty(profile), minutes_per_problem(profile)
    matched_gaps: set[str] = set()
    plan: list[PlanTopic] = []

    for subject in weights:
        for position, topic in enumerate(curriculum[subject].topics):
            if level not in topic.levels or (topic.roles and profile.target_role not in topic.roles):
                continue
            if topic.track and topic.track != project_track(profile):
                continue
            if topic.only_if == "language_basics" and profile.language_comfort > 2:
                continue
            hit = [(skill, source) for skill, source in gaps if matches(topic, skill)]
            matched_gaps.update(skill for skill, _ in hit)
            factor = _knowledge_factor(profile, subject, interview_scores, has_gap=bool(hit))
            if subject in CS_SUBJECTS and profile.degree in ("bca", "bsc", "other"):
                factor *= NOT_TAUGHT_FACTOR
            learn = round(topic.minutes * factor)
            practice = round(topic.problems.get(difficulty, 0) * per_problem * factor)
            details = {"resource": (topic.resource or curriculum[subject].resource).model_dump()}
            if topic.suggested:
                details["suggested"] = topic.suggested
            if topic.interview:
                details["interview"] = topic.interview
            plan.append(PlanTopic(
                topic_id=topic.id, subject=subject, priority=PROMOTE[topic.priority] if hit else topic.priority,
                title=topic.title.format(language=LANGUAGES[profile.language]), position=position,
                planned_minutes=max(learn + practice, 10), learn_minutes=learn if subject == "dsa" else 0,
                prerequisites=topic.prerequisites, details=details,
                source=("interview_gap" if hit[0][1] == "interview" else "resume_gap") if hit else "curriculum",
            ))

    plan += _checkpoints(plan, curriculum)
    plan += _gap_topics([g for g in gaps if g[0] not in matched_gaps], weights)
    return plan


def _knowledge_factor(profile: PlannerProfile, subject: str, interview_scores: dict[str, int], has_gap: bool) -> float:
    rating = profile.ratings.get(RATING_FOR[subject], 0) if subject in RATING_FOR else 0
    factor = KNOWLEDGE_FACTOR[rating]
    weak_in_interview = interview_scores.get(subject, 100) < 60
    return max(factor, EVIDENCE_FLOOR) if has_gap or weak_in_interview else factor


def _checkpoints(plan: list[PlanTopic], curriculum) -> list[PlanTopic]:
    """After a CS subject's last topic: a short mock interview on that subject (practice testing)."""
    out = []
    for subject in CS_SUBJECTS:
        ids = [t.topic_id for t in plan if t.subject == subject]
        if ids:
            out.append(PlanTopic(
                topic_id=f"{subject}.checkpoint", subject=subject, priority="must", source="checkpoint",
                title=f"Checkpoint: mock interview on {curriculum[subject].label}", position=len(ids),
                planned_minutes=CHECKPOINT_MINUTES, prerequisites=ids,
                details={"interview": {"track": "fundamentals", "topics": [subject]}},
            ))
    return out


def _gap_topics(unmatched: list[tuple[str, str]], weights: dict[str, float]) -> list[PlanTopic]:
    """Gaps with no curriculum topic (e.g. "Docker" from a JD) become small topics of their own."""
    out = []
    for i, (skill, source) in enumerate(unmatched[:MAX_GAP_TOPICS]):
        if source == "interview":
            subject, title = "practice", f"Practise: {skill} (answer three questions out loud, then a mock)"
        else:
            subject = "role" if "role" in weights else "projects"
            title = f"Learn {skill} basics and use it in your project"
        out.append(PlanTopic(
            topic_id=f"gap.{i}", subject=subject, title=title, priority="should", position=100 + i,
            planned_minutes=GAP_TOPIC_MINUTES, source="interview_gap" if source == "interview" else "resume_gap",
            details={"gap": skill},
        ))
    return out
