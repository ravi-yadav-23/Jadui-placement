"""The curriculum (curriculum/*.yaml) and the subject weights (curriculum/weights.yaml).

Loaded once and validated, so a typo fails at startup and in the tests instead of producing a broken plan:
  * topic ids are unique; every prerequisite exists; prerequisites have no cycles
  * every weights row adds up to 100 and only names known subjects
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

CURRICULUM_DIR = Path(__file__).parent / "curriculum"
CURRICULUM_VERSION = "v1"
LEVELS = ["entry", "mid", "senior"]

Level = Literal["entry", "mid", "senior"]
Priority = Literal["must", "should", "nice"]


class Resource(BaseModel):
    title: str
    url: str


class Topic(BaseModel):
    id: str
    subject: str = ""                      # filled in from the file
    title: str
    minutes: int                           # learning time from zero (DSA: theory part only)
    problems: dict[str, int] = Field(default_factory=dict)   # DSA: service / product / top_product
    prerequisites: list[str] = Field(default_factory=list)
    levels: list[Level] = Field(default_factory=lambda: list(LEVELS))
    priority: Priority = "must"
    aliases: list[str] = Field(default_factory=list)          # lowercase phrases used to match skill gaps
    suggested: list[str] = Field(default_factory=list)        # DSA: problems to start with
    resource: Resource | None = None
    roles: list[str] = Field(default_factory=list)            # role add-ons only
    track: Literal["build", "deepen"] | None = None           # projects only
    only_if: Literal["language_basics"] | None = None
    interview: dict | None = None                             # practice topics: which mock interview to open


class Subject(BaseModel):
    subject: str
    label: str
    resource: Resource
    topics: list[Topic]


@lru_cache(maxsize=1)
def load_curriculum() -> dict[str, Subject]:
    subjects: dict[str, Subject] = {}
    for path in sorted(CURRICULUM_DIR.glob("*.yaml")):
        if path.name == "weights.yaml":
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for raw in data.get("subjects", [data]):
            subject = Subject.model_validate(raw)
            for topic in subject.topics:
                topic.subject = subject.subject
            subjects[subject.subject] = subject
    _validate(subjects)
    return subjects


def all_topics() -> dict[str, Topic]:
    return {t.id: t for s in load_curriculum().values() for t in s.topics}


def _validate(subjects: dict[str, Subject]) -> None:
    topics = [t for s in subjects.values() for t in s.topics]
    ids = [t.id for t in topics]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"Duplicate topic ids: {sorted(duplicates)}")
    by_id = {t.id: t for t in topics}
    for topic in topics:
        missing = [p for p in topic.prerequisites if p not in by_id]
        if missing:
            raise ValueError(f"{topic.id}: unknown prerequisites {missing}")

    # Cycle check: depth-first search; reaching a topic that is still "in progress" means a cycle.
    state: dict[str, str] = {}

    def visit(topic_id: str) -> None:
        if state.get(topic_id) == "done":
            return
        if state.get(topic_id) == "visiting":
            raise ValueError(f"Prerequisite cycle through {topic_id}")
        state[topic_id] = "visiting"
        for prerequisite in by_id[topic_id].prerequisites:
            visit(prerequisite)
        state[topic_id] = "done"

    for topic_id in by_id:
        visit(topic_id)


@lru_cache(maxsize=1)
def load_weights() -> dict:
    weights = yaml.safe_load((CURRICULUM_DIR / "weights.yaml").read_text(encoding="utf-8"))
    rows = [*weights["entry"].values(), weights["mid"], weights["senior"], *weights["student_year"].values()]
    known = set(load_curriculum())
    for row in rows:
        if sum(row.values()) != 100:
            raise ValueError(f"Weights must add up to 100: {row}")
        if set(row) - known:
            raise ValueError(f"Unknown subjects in weights: {set(row) - known}")
    return weights
