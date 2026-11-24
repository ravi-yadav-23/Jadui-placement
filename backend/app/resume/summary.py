"""Read-only overview of the resume pillar, for other pillars (dashboard, planner, coach chat)."""

from collections import Counter

from app.core.db import Database
from app.resume.schemas import RecentAnalysis, ResumeOverview

ANALYSIS_COLUMNS = "id,resume_id,jd_id,mode,target_role,status,overall_score,created_at"


def overview(db: Database, user_id: str) -> ResumeOverview:
    resumes = db.list("resumes", user_id, columns="id,title,created_at", limit=100)
    titles = {r["id"]: r["title"] for r in resumes}
    jd_titles = {j["id"]: j.get("title") for j in db.list("job_descriptions", user_id, columns="id,title", limit=100)}
    analyses = [a for a in db.list("resume_analyses", user_id, columns=ANALYSIS_COLUMNS, limit=30)
                if a["status"] == "done"]
    gaps = db.list("skill_gaps", user_id, columns="skill,resolved_at,created_at", limit=300)
    open_gaps = Counter(g["skill"] for g in gaps if not g.get("resolved_at"))
    return ResumeOverview(
        resume_count=len(resumes),
        recent=[RecentAnalysis(
            id=a["id"], resume_id=a["resume_id"], resume_title=titles.get(a["resume_id"], "Resume"),
            mode=a["mode"], target_role=a.get("target_role"), jd_title=jd_titles.get(a.get("jd_id")),
            overall_score=a["overall_score"], created_at=a["created_at"],
        ) for a in analyses[:10]],
        top_gaps=[skill for skill, _ in open_gaps.most_common(8)],
    )


def recent_general_scores(db: Database, user_id: str, limit: int = 5) -> list[int]:
    return [a.overall_score for a in overview(db, user_id).recent if a.mode == "general"][:limit]
