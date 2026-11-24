"""Delivery insights: counted by code, free, shown as information (never part of the score).

  words per minute  = words / (duration_seconds / 60)       only when a duration is known (voice)
  filler words      = occurrences of data/fillers.yaml phrases ("um", "basically", "you know", ...)
  repeated words    = content words used 3+ times (the Google Interview Warmup idea)
  terms             = technologies from the resume skills taxonomy that the answer mentions
"""

from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import yaml

from app.interview.schemas import Delivery
from app.resume.pipeline.taxonomy import find_skills

FILLERS_FILE = Path(__file__).parent / "data" / "fillers.yaml"
MIN_DURATION_SECONDS = 5  # shorter recordings give meaningless pace numbers


@lru_cache(maxsize=1)
def _word_lists() -> tuple[list[re.Pattern], set[str]]:
    data = yaml.safe_load(FILLERS_FILE.read_text(encoding="utf-8"))
    patterns = [re.compile(rf"\b{re.escape(f)}\b") for f in data["fillers"]]
    return patterns, set(data["stopwords"])


def delivery_metrics(answer: str, duration_seconds: int | None = None) -> Delivery:
    lower = answer.lower()
    words = re.findall(r"[a-z0-9']+", lower)
    fillers, stopwords = _word_lists()
    counts = Counter(w for w in words if len(w) > 2 and w not in stopwords)
    wpm = None
    if duration_seconds and duration_seconds >= MIN_DURATION_SECONDS:
        wpm = round(len(words) / (duration_seconds / 60))
    return Delivery(
        words=len(words),
        wpm=wpm,
        fillers=sum(len(p.findall(lower)) for p in fillers),
        repeated=[w for w, n in counts.most_common(5) if n >= 3],
        terms=sorted(find_skills(answer)),
    )
