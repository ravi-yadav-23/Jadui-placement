"""Persona eval for the planner: build a plan for each persona and check it (no LLM, runs in CI).

    python -m evals.planner.run
    python -m evals.planner.run --out ../docs/evals/planner-v1.md

For each persona: weeks, usable hours/week, feasibility, subject shares of scheduled learning time, and the
scheduler properties (never over a day's capacity, prerequisites first, nothing on rest/busy days).
Exits with code 1 if any check fails.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.planner.builder import build_plan  # noqa: E402
from app.planner.capacity import build_calendar  # noqa: E402
from app.planner.schemas import PlannerProfile  # noqa: E402

START = date(2026, 12, 7)


def resolve_dates(raw: dict) -> dict:
    """'+28' means 28 days after START, so the file never goes stale."""
    def fix(value):
        if isinstance(value, str) and value.startswith("+"):
            return (START + timedelta(days=int(value[1:]))).isoformat()
        if isinstance(value, dict):
            return {k: fix(v) for k, v in value.items()}
        if isinstance(value, list):
            return [fix(v) for v in value]
        return value
    return fix(raw)


def check(persona: dict) -> tuple[str, list[str]]:
    profile = PlannerProfile.model_validate(resolve_dates(persona["profile"]))
    built = build_plan(profile, START, [], {})
    capacity = dict(build_calendar(profile, START, built.target, 0.85))
    per_day, by_subject = defaultdict(int), defaultdict(int)
    for task in built.schedule.tasks:
        per_day[task.date] += task.minutes
        if task.topic_id and task.kind != "review":
            by_subject[task.subject] += task.minutes
    total = sum(by_subject.values()) or 1
    shares = {s: m / total for s, m in by_subject.items()}

    problems = []
    if any(m > capacity[d] for d, m in per_day.items()):
        problems.append("a day is over capacity")
    topics = {t.topic_id: t for t in built.topics if t.status != "cut"}
    starts = {}
    for task in built.schedule.tasks:
        if task.topic_id and task.kind != "review":
            starts.setdefault(task.topic_id, task.date)
    for topic_id, start in starts.items():
        if any(p in topics and built.schedule.finished_on[p] > start for p in topics[topic_id].prerequisites):
            problems.append(f"{topic_id} starts before a prerequisite")
    expect = persona.get("expect", {})
    for subject, low in expect.get("share_min", {}).items():
        if shares.get(subject, 0) < low:
            problems.append(f"{subject} share {shares.get(subject, 0):.2f} < {low}")
    for subject, high in expect.get("share_max", {}).items():
        if shares.get(subject, 0) > high:
            problems.append(f"{subject} share {shares.get(subject, 0):.2f} > {high}")
    if "fits" in expect and built.feasibility.fits != expect["fits"]:
        problems.append(f"fits={built.feasibility.fits}, expected {expect['fits']}")

    weeks = ((built.target - built.start).days + 1) / 7
    top = ", ".join(f"{s} {100 * v:.0f}%" for s, v in sorted(shares.items(), key=lambda kv: -kv[1])[:4])
    row = (f"| {persona['name']} | {weeks:.0f} | {built.usable_minutes / 60 / weeks:.1f} | "
           f"{'yes' if built.feasibility.fits else 'no (' + str(len(built.feasibility.cut)) + ' cut)'} | {top} | "
           f"{'✅' if not problems else '❌ ' + '; '.join(problems)} |")
    return row, problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="write the markdown report here")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    personas = yaml.safe_load(Path(__file__).with_name("personas.yaml").read_text(encoding="utf-8"))["personas"]
    lines = [f"# Planner persona eval — start {START}", "",
             "| persona | weeks | usable h/week | fits | top subjects (share of learning time) | checks |",
             "|---|---|---|---|---|---|"]
    failed = 0
    for persona in personas:
        row, problems = check(persona)
        lines.append(row)
        failed += bool(problems)
    lines += ["", f"**{len(personas) - failed}/{len(personas)} personas pass.**"]
    report = "\n".join(lines) + "\n"
    print(report)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
