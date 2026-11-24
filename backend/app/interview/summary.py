"""Read-only overview of the interview pillar, for the dashboard, planner and coach chat."""

from __future__ import annotations

from collections import Counter, defaultdict

from app.core.db import Database
from app.interview.schemas import InterviewOverview, RecentInterview


def overview(db: Database, user_id: str) -> InterviewOverview:
    rows = db.list("interviews", user_id, columns="id,track,status,score,report,created_at", limit=30)
    done = [r for r in rows if r["status"] == "completed" and r.get("report") and r["report"]["questions"]]

    topics: dict[str, list[int]] = defaultdict(list)
    dimensions: dict[str, list[float]] = defaultdict(list)
    for row in done:
        for topic, score in row["report"]["topics"].items():
            topics[topic].append(score)
        for name, anchor in row["report"]["dimensions"].items():
            dimensions[name].append(anchor)
    dimension_means = {name: sum(v) / len(v) for name, v in dimensions.items()}

    gaps = db.list("skill_gaps", user_id, columns="skill,source,resolved_at,created_at", limit=300, source="interview")
    open_gaps = Counter(g["skill"] for g in gaps if not g.get("resolved_at"))
    last_five = [r["score"] for r in done[:5]]
    return InterviewOverview(
        completed_count=len(done),
        recent=[RecentInterview(id=r["id"], track=r["track"], score=r["score"], created_at=r["created_at"])
                for r in done[:10]],
        average_score=round(sum(last_five) / len(last_five)) if last_five else None,
        topic_averages={t: round(sum(v) / len(v)) for t, v in topics.items()},
        weakest_dimension=min(dimension_means, key=dimension_means.get) if dimension_means else None,
        open_gaps=[skill for skill, _ in open_gaps.most_common(8)],
    )


def recent_scores(db: Database, user_id: str, limit: int = 5) -> list[int]:
    return [r.score for r in overview(db, user_id).recent][:limit]
