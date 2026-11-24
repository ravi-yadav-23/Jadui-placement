"""Evaluate the resume screener's AI steps against a labeled set (cases.yaml).

    python -m evals.resume.run                 # real LLM (uses your API keys, costs a little)
    python -m evals.resume.run --fake          # checks the harness itself, no API calls
    python -m evals.resume.run --cases evals/resume/private/cases.yaml   # your own (gitignored) cases

Metrics:
  extraction  - bullet recall, skill precision/recall, share of bullets grounded in the text
  jd parsing  - must-have / nice-to-have skill precision/recall, knockout types found
  matching    - tier accuracy (exact and within one tier)
  stability   - std-dev of the general score over N identical runs (target <= 3 points)
  guard       - how often the truth guard had to fix or reject an AI rewrite
  cost        - average latency and tokens per LLM call, by prompt
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.core.db import InMemoryDatabase  # noqa: E402
from app.llm.client import PROMPT_VERSIONS, get_llm  # noqa: E402
from app.resume.pipeline.contacts import extract_contacts  # noqa: E402
from app.resume.pipeline.extract_pdf import extract_pdf  # noqa: E402
from app.resume.pipeline.jd_parse import parse_jd  # noqa: E402
from app.resume.pipeline.knockouts import check_knockouts  # noqa: E402
from app.resume.pipeline.lint import unsupported_skills  # noqa: E402
from app.resume.pipeline.match import match_profile  # noqa: E402
from app.resume.pipeline.review import review_profile  # noqa: E402
from app.resume.pipeline.scoring import general_score, jd_score  # noqa: E402
from app.resume.pipeline.structure import normalize, structure_resume  # noqa: E402
from app.resume.pipeline.taxonomy import normalize_skill  # noqa: E402
from app.resume.schemas import Check  # noqa: E402
from tests.resume.builders import single_column_pdf  # noqa: E402

TIERS = ["not_a_fit", "stretch", "good", "strong"]


def precision_recall(found: set[str], expected: set[str]) -> tuple[float, float]:
    hits = len(found & expected)
    return (hits / len(found) if found else 1.0, hits / len(expected) if expected else 1.0)


def canonical_set(items) -> set[str]:
    return {normalize_skill(i) for i in items}


def _avg(rows: list[dict], key: str) -> float:
    return statistics.mean(r[key] or 0 for r in rows) if rows else 0.0


def pct(value: float) -> str:
    return f"{100 * value:.0f}%"


def evaluate(cases: dict, runs: int) -> str:
    db = InMemoryDatabase()                      # only used to collect llm_calls logs
    llm = get_llm(db, None)
    lines = [f"# Resume screener eval — {date.today()}", "",
             f"Model: `{'fake' if settings.LLM_PROVIDER == 'fake' else settings.LLM_PRIMARY_MODEL}` · "
             f"prompts: {', '.join(f'{k} {v}' for k, v in PROMPT_VERSIONS.items())} · general-review runs: {runs}", ""]

    # ---- extraction + general review ----
    lines += ["## Extraction and general review", "",
              "| resume | bullet recall | skill P / R | grounded | score (mean ± sd) | guard fixes |",
              "|---|---|---|---|---|---|"]
    profiles, totals = {}, defaultdict(list)
    for name, case in cases["resumes"].items():
        doc = extract_pdf(single_column_pdf(case["text"].strip()))
        contacts = extract_contacts(doc.text, doc.links)
        profile = structure_resume(llm, doc.text, contacts)
        profiles[name] = profile

        bullets = [normalize(b.text) for b in profile.all_bullets()]
        expected = [normalize(b) for b in case["labels"]["bullets"]]
        recall = sum(any(e in b for b in bullets) for e in expected) / len(expected)
        skill_p, skill_r = precision_recall(canonical_set(profile.skills), canonical_set(case["labels"]["skills"]))
        all_bullets = profile.all_bullets()
        grounded = sum(b.grounded for b in all_bullets) / len(all_bullets) if all_bullets else 0.0

        scores, fixes, rewrites = [], 0, 0
        for _ in range(runs):
            feedback, _, _ = review_profile(llm, profile, None)
            overall, _ = general_score([Check(id="x", status="pass", message="")], feedback, profile, contacts,
                                       len(unsupported_skills(profile)))
            scores.append(overall)
            fixes += sum(1 for f in feedback if f.guard_notes)
            rewrites += sum(1 for f in feedback if f.rewrite or f.guard_notes)
        sd = statistics.pstdev(scores)
        for key, value in (("recall", recall), ("skill_p", skill_p), ("skill_r", skill_r), ("grounded", grounded),
                           ("sd", sd)):
            totals[key].append(value)
        totals["fixes"].append(fixes)
        totals["rewrites"].append(rewrites)
        lines.append(f"| {name} | {pct(recall)} | {pct(skill_p)} / {pct(skill_r)} | {pct(grounded)} | "
                     f"{statistics.mean(scores):.1f} ± {sd:.1f} | {fixes}/{rewrites} |")

    mean = {k: statistics.mean(v) for k, v in totals.items()}
    lines += ["", f"**Averages:** bullet recall {pct(mean['recall'])} · skill precision {pct(mean['skill_p'])} · "
              f"skill recall {pct(mean['skill_r'])} · grounded {pct(mean['grounded'])} · "
              f"score sd {mean['sd']:.1f} points (target ≤ 3) · guard intervened on "
              f"{sum(totals['fixes'])} of {sum(totals['rewrites'])} rewrites", ""]

    # ---- JD parsing ----
    lines += ["## JD parsing", "", "| jd | must P / R | nice P / R | knockouts (found / expected) |",
              "|---|---|---|---|"]
    parsed = {}
    for name, case in cases["jds"].items():
        jd = parse_jd(llm, case["text"].strip())
        parsed[name] = jd
        musts = {s for r in jd.requirements if r.kind == "must" for s in r.skills}
        nices = {s for r in jd.requirements if r.kind == "nice" for s in r.skills}
        must_p, must_r = precision_recall(musts, canonical_set(case["labels"]["must_skills"]))
        nice_p, nice_r = precision_recall(nices, canonical_set(case["labels"]["nice_skills"]))
        found = sorted({k.type for k in jd.knockouts})
        lines.append(f"| {name} | {pct(must_p)} / {pct(must_r)} | {pct(nice_p)} / {pct(nice_r)} | "
                     f"{', '.join(found) or '-'} / {', '.join(sorted(case['labels']['knockouts'])) or '-'} |")

    # ---- matching ----
    lines += ["", "## JD matching", "", "| resume × jd | score | tier | expected |", "|---|---|---|---|"]
    exact = near = 0
    for pair in cases["pairs"]:
        profile, jd = profiles[pair["resume"]], parsed[pair["jd"]]
        output = match_profile(llm, profile, jd)
        knockouts = check_knockouts(jd.knockouts, profile)
        is_student = any((e.grad_year or 0) >= date.today().year for e in profile.education)
        total, tier, _, _ = jd_score(output.requirements, knockouts, output.role_alignment, jd.seniority,
                                     jd.min_years, is_student)
        distance = abs(TIERS.index(tier) - TIERS.index(pair["tier"]))
        exact += distance == 0
        near += distance <= 1
        lines.append(f"| {pair['resume']} × {pair['jd']} | {total} | {tier} | {pair['tier']} |")
    n = len(cases["pairs"])
    lines += ["", f"**Tier accuracy:** exact {exact}/{n} · within one tier {near}/{n}", ""]

    # ---- cost ----
    lines += ["## Latency and tokens per call", "", "| prompt | calls | ok | avg latency | avg in / out tokens |",
              "|---|---|---|---|---|"]
    by_prompt = defaultdict(list)
    for row in db.logs.get("llm_calls", []):
        by_prompt[row["purpose"]].append(row)
    for purpose, rows in sorted(by_prompt.items()):
        ok = [r for r in rows if r["ok"]]
        lines.append(f"| {purpose} | {len(rows)} | {len(ok)} | {_avg(ok, 'latency_ms'):.0f} ms | "
                     f"{_avg(ok, 'input_tokens'):.0f} / {_avg(ok, 'output_tokens'):.0f} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(Path(__file__).with_name("cases.yaml")))
    parser.add_argument("--runs", type=int, default=3, help="general-review repetitions for the stability metric")
    parser.add_argument("--fake", action="store_true", help="use the fake LLM (no API calls)")
    parser.add_argument("--out", help="write the markdown report here (default: print only)")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    if args.fake:
        settings.LLM_PROVIDER = "fake"
    report = evaluate(yaml.safe_load(Path(args.cases).read_text(encoding="utf-8")), args.runs)
    print(report)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
