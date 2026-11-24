"""The curated question bank (data/fundamentals.yaml + data/behavioral.yaml).

    pick_questions(topics=["os", "dbms"], difficulty="any", count=3, exclude=recent_ids, seed=42)

Selection is deterministic for a given seed (the seed is stored on the interview row, so a
session can be reproduced), skips questions you saw recently, and spreads picks across topics.
"""

from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).parent / "data"


class BankQuestion(BaseModel):
    id: str
    topic: Literal["os", "dbms", "cn", "oop", "behavioral"]
    difficulty: Literal["easy", "medium", "hard"]
    concept: str
    question: str
    key_points: list[str] = Field(min_length=2, max_length=6)


@lru_cache(maxsize=1)
def load_bank() -> tuple[BankQuestion, ...]:
    """Load and validate both files. A typo (unknown topic, duplicate id) raises at startup and in tests."""
    questions: list[BankQuestion] = []
    for name in ("fundamentals.yaml", "behavioral.yaml"):
        raw = yaml.safe_load((DATA_DIR / name).read_text(encoding="utf-8"))
        questions += [BankQuestion.model_validate(item) for item in raw]
    ids = [q.id for q in questions]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"Duplicate question ids in the bank: {sorted(duplicates)}")
    return tuple(questions)


def pick_questions(topics: list[str], difficulty: str, count: int, exclude: set[str], seed: int) -> list[BankQuestion]:
    """Pick `count` questions from `topics`, round-robin across topics so one topic doesn't dominate."""
    rng = random.Random(seed)
    pool = [q for q in load_bank() if q.topic in topics and (difficulty == "any" or q.difficulty == difficulty)]
    fresh = [q for q in pool if q.id not in exclude]
    if len(fresh) < count:  # not enough unseen questions: allow repeats rather than a short session
        fresh = pool

    by_topic: dict[str, list[BankQuestion]] = {}
    for question in fresh:
        by_topic.setdefault(question.topic, []).append(question)
    for bucket in by_topic.values():
        rng.shuffle(bucket)
    order = [t for t in topics if t in by_topic]
    rng.shuffle(order)

    picked: list[BankQuestion] = []
    while len(picked) < count and any(by_topic[t] for t in order):
        for topic in order:
            if by_topic[topic] and len(picked) < count:
                picked.append(by_topic[topic].pop())
    return picked
