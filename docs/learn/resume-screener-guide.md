# Resume Screener v2: how it works (study guide)

Read this top to bottom once with the code open beside it. Every section links to the files involved.
The goal: you can explain any part of this system, and why it was built that way, in an interview.

---

## 1. The 60-second pitch

> "It's the resume pillar of my AI career coach. You upload a PDF or DOCX. A layout-aware parser
> extracts the text in reading order, even for two-column resumes, and 16 deterministic checks tell you
> whether a parser can read the file. An LLM turns the text into structured sections; every bullet it
> returns is verified against the original text, so hallucinated bullets are caught.
>
> Then you can run a general review or match against a job description. Most of the score is computed
> by rules. The LLM only rates substance on an anchored 1–5 rubric. For JD matching, every requirement is
> marked proven, partial or missing, and I quote the exact bullet that proves it.
>
> The part I'm proudest of is the truth guard: AI rewrites may rephrase your bullet but can never add a
> number, technology, company or leadership claim. Invented numbers become `[X]` placeholders that you
> fill in yourself. Names and contact details are redacted before any LLM call, to reduce name-based
> bias. It's tested with 107 unit/API tests, a Playwright E2E test, and an eval harness on a labeled set."

---

## 2. The big picture

```
Browser (Next.js, TypeScript)
  │  fetch with Supabase access token  (frontend/src/lib/api/client.ts)
  ▼
FastAPI  /api/v2/...                    (backend/app/resume/api.py)
  │  auth: verify JWT, no demo fallback (backend/app/core/auth.py)
  │  thin routes -> service functions   (service.py, jd.py, analysis.py)
  │  long work runs as a BackgroundTask; the browser polls until status = ready/done
  ▼
Pipeline steps (pure functions)         (backend/app/resume/pipeline/*.py)
  │  deterministic: extract, checks, contacts, sections, lint, guard, scoring, knockouts
  │  LLM (via one client):  structure, review, jd_parse, jd_match
  ▼
LLMClient                               (backend/app/llm/client.py)
  │  versioned prompt files, Pydantic validation, repair retry, Gemini -> Groq fallback, call log
  ▼
Database layer                          (backend/app/core/db.py)
     every call takes user_id; Supabase in production, in-memory dicts in tests
```

**Rule of thumb used everywhere:** *if something can be counted, code counts it; the LLM only does what
needs judgement, and code checks the LLM's answer.*

---

## 3. Walkthrough: uploading a resume

| Step | What happens | Where |
|---|---|---|
| 1 | The dropzone sends the file as `multipart/form-data` to `POST /api/v2/resumes` | `features/resume/components/UploadDropzone.tsx`, `hooks.ts` → `useUploadResume` |
| 2 | Auth: the JWT is verified (HS256 secret or JWKS public keys). No token → 401 | `app/core/auth.py` → `get_current_user` |
| 3 | Validate by **bytes, not file name**: `%PDF-` or a zip containing `word/document.xml`; size cap | `pipeline/ingest.py` → `detect_file_kind`, `validate_upload` |
| 4 | SHA-256 of the bytes. Same file again → return the existing row (dedupe). Same file that *failed* → retry it | `service.py` → `create_resume` |
| 5 | Daily upload limit (counts rows in the last 24 h); page cap | `service.py` → `enforce_daily_limit` |
| 6 | Save the original to private storage `resumes/{user_id}/{id}.pdf`, insert the row with `status=queued`, return **202** | `service.py`, `core/db.py` |
| 7 | **Background task** `process_resume` starts after the response is sent | `api.py` → `background.add_task` |
| 8 | Extract text in reading order (see §3.1) | `pipeline/extract_pdf.py`, `extract_docx.py` |
| 9 | Contacts by regex; section headings by alias list | `pipeline/contacts.py`, `sections.py`, `data/section_aliases.yaml` |
| 10 | 16 parse-health checks → saved **before** the LLM step, so they survive an LLM outage | `pipeline/checks.py` |
| 11 | Redact name + contacts, LLM structures the text, code grounds every bullet (see §3.2) | `pipeline/redact.py`, `structure.py` |
| 12 | `status=ready`. Meanwhile the browser polls `GET /resumes/{id}` every 1.5 s | `hooks.ts` → `useResume` (`refetchInterval`) |

### 3.1 Reading order for two-column PDFs (`extract_pdf.py`)
A PDF stores text in whatever order the generator wrote it, so naive extraction interleaves two
columns line by line. Fix:
1. Get every **line** with its bounding box. Blocks are not enough: PyMuPDF put a left-column line and a
   right-column line in the same block in our test.
2. `find_gutter`: try x positions from 25% to 75% of the page width. A gutter is an x that almost no line
   crosses (≤15% of lines) with ≥4 lines on each side.
3. `order_lines`: lines crossing the gutter (like the name header) are *separators*. Between separators,
   output the whole left column top-to-bottom, then the right column.
4. Keep `\n` between lines. The old code collapsed all whitespace, which silently broke section detection.

### 3.2 Structuring with grounding (`structure.py`)
- The LLM gets the **redacted** text (`[NAME]`, `[EMAIL]`, ...) and must return a `ProfileDraft`
  (Pydantic). The prompt says: extract verbatim, never rewrite, null if absent.
- `build_profile` assigns stable IDs (`exp0.b1` = experience 0, bullet 1) and checks **grounding**: the
  bullet must appear in the normalised raw text (exact substring, or rapidfuzz partial ratio ≥ 90 for
  bullets ≥ 20 chars). `normalize` re-joins hyphenated line breaks and collapses whitespace, because
  bullets wrap across lines in real PDFs.
- Ungrounded bullets are kept but flagged and **excluded from scoring**. The user can fix them in the
  profile editor; saving marks everything as user-confirmed (`reassign_ids`).
- CGPA and graduation year must literally appear in the text, otherwise they're dropped (a wrong
  CGPA would produce a wrong knockout result).

---

## 4. Walkthrough: general review (`analysis.py` → `run_general_review`)

1. **Cache check**: `input_hash` = SHA-256 of (profile, mode, target role, JD hash, prompt versions, model).
   A finished analysis with the same hash is returned with **200** instead of calling the LLM again.
2. `lint.py`: deterministic issues per bullet: `no_metric`, `weak_start`, `pronoun`, `passive`,
   `length`, `buzzword`, `vague`. Word lists live in `data/lint_words.yaml`.
   Resume-level: repeated opening verbs; skills listed but never shown. That check uses the taxonomy's
   `implies` (a FastAPI bullet is evidence of Python), and only counts concrete technologies, not concepts
   like DSA.
3. `review.py`: **one** LLM call with all grounded bullets (IDs + lint issues). It returns per bullet:
   specificity, technical depth and outcome (1–5 with written anchors in the prompt), extra issues,
   a rewrite and coach questions.
4. `guard.py` runs on every rewrite (§6).
5. `scoring.py` → `general_score`, a documented formula. 75 of 100 points are deterministic:

| Part | Max | Formula |
|---|---|---|
| Parse health | 20 | 20 − 6 × fails − 2 × warns |
| Impact | 25 | 15 × min(1, quantified / (0.5 × bullets)) + 10 × strong-verb ratio |
| Clarity | 15 | 15 × bullets without length/pronoun/passive/buzzword/vague issues ÷ bullets |
| Completeness | 15 | 3 each: email, education, skills, experience-or-projects, LinkedIn + GitHub |
| Substance (LLM) | 25 | 25 × mean((spec + depth + outcome) / 15) − 2 per unsupported skill (max 6) |

Every sub-score carries an `explanation` string. The UI shows it under "How is this calculated?".

---

## 5. Walkthrough: JD match

**Parsing the JD** (`jd.py`, `pipeline/jd_parse.py`): saved once, de-duplicated by text hash, parsed in
the background. The LLM splits requirements into **must/nice** and extracts **knockouts**. Code then:
- normalises skill names through the taxonomy and adds skills the LLM forgot to list for a requirement;
- **drops any knockout whose value doesn't appear in the JD text**, and any `min_years` not stated.

**Matching** (`pipeline/match.py` → `match_profile`):
1. **Rules first** (`rule_match`): if *every* skill a requirement names appears in some grounded bullet
   (counting implied skills), it's `strong`, decided by code, and the bullet is cited.
2. **One LLM call** judges the rest (including non-skill requirements like "deploying models at scale"),
   gives role alignment 0–5, and proposes up to 5 tailored rewrites plus a summary line.
3. **Validate the judge** (`validate_judgment`): cited bullet IDs must exist. "Strong" with no valid
   evidence becomes "missing"; a missing skill that *is* listed on the resume becomes `listed_only`.
4. `knockouts.py`: CGPA (handles /4, /10 and % cutoffs), graduation batch, location. The result is
   ok / conflict / unknown. Notice period and work authorization are always "unknown": the resume can't
   answer those.
5. `scoring.py` → `jd_score`:

| Part | Max | Formula |
|---|---|---|
| Must-haves | 45 | 45 × Σ(strong 1, partial 0.5, listed_only 0.5) ÷ musts |
| Nice-to-haves | 15 | same over nice-to-haves (full marks if none) |
| Evidence depth | 15 | proven musts ÷ covered musts |
| Experience fit | 10 | 10 entry-level; 0 if a mid/senior role and the resume is a student's; else 5 |
| Role alignment | 5 | LLM 0–5 |
| Knockouts | 10 | 10 none · 5 unknown · 0 any conflict |

   Tiers: ≥80 strong, ≥60 good, ≥40 stretch, else not a fit. Each tier has an **honest message**. For
   "not a fit": *don't stretch your resume; here's what to learn.*
6. Missing requirements are written to `skill_gaps`. The future planner pillar turns them into tasks.

---

## 6. The truth guard (`pipeline/guard.py`): explain this one well

Rules for any AI rewrite, compared against the original bullet:
1. **Numbers**: a number not in the original is replaced by `[X]`, plus a note. A made-up metric
   never reaches the user.
2. **Technologies**: a technology not in the original bullet or that job's/project's stack → rewrite rejected.
3. **Names**: a capitalised token (company or product) not in the original and not a known skill → rejected.
4. **Ownership**: starting with Led/Architected/Spearheaded… when the original didn't claim
   leadership → rejected.

A rejected rewrite still leaves the coach questions ("How many users used this?"). That's the honest
alternative to inventing numbers. Tested with table tests plus a randomized property test:
300 random rewrites, and no number outside the original ever survives (`test_lint_and_guard.py`).

---

## 7. Design decisions and trade-offs (interview answers)

**Why not let the LLM do everything?** Cost, speed, repeatability, and trust. Counting digits or checking
for an email doesn't need a model. Deterministic parts give the same answer every time and are unit-tested.
The LLM part is constrained by a schema and a rubric, then checked by code.

**Why Pydantic schemas for LLM output?** The model must return JSON matching the schema. Gemini receives
the JSON Schema directly. If validation fails, we retry once with the validation error appended ("repair
retry"); if it fails again, we fall back to the next provider. Errors are surfaced, never swallowed.

**Why versioned prompt files?** Every analysis stores which prompt versions and model produced it.
Change a prompt → bump `v1` to `v2` → old results stay explainable, and the cache key changes automatically.

**Why redact names?** A UW study (2024) found embedding-based screening preferred white-associated names 85%
of the time. The model never needs the name to judge content, and contacts come from regex anyway.

**Why BackgroundTasks instead of Celery?** One small instance on free hosting; the job takes 5–20 s. The
upload returns 202 and the UI polls. Trade-off: a restart loses running jobs. Mitigation: a job still
"processing" after 10 minutes is shown as failed and can be retried. Upgrade path: the job functions are
plain functions, so a Celery worker could call them unchanged.

**Why does every DB call take `user_id`?** The old code had IDOR bugs: you could read another user's
data by ID. Now a query that forgets ownership can't be written. Supabase RLS policies are a second layer.

**Why an in-memory database implementation?** Tests run in ~3 s with no database, and the E2E test runs
the whole app without touching Supabase. Same interface (`Database` protocol), two implementations.

**Why cache by input hash?** Identical inputs give an identical result, with zero cost and full reproducibility.

**Why generate TypeScript types from OpenAPI?** The old frontend read fields that didn't exist (`analyzeData.analysis`).
Now `npm run gen:api` regenerates types, and the type check fails if backend and frontend disagree.

**Why a fake LLM provider?** Deterministic tests and E2E. Real model quality is measured separately by
the eval harness, which is the right tool for a non-deterministic component.

---

## 8. Likely interview questions

1. *How do you stop the LLM from hallucinating bullets?* Grounding: every extracted bullet must
   exist in the raw text (exact or fuzzy ≥ 90). Ungrounded ones are flagged and excluded from scoring.
2. *How do you stop it inventing metrics in rewrites?* The truth guard (§6), deterministic and property-tested.
3. *Is your score just the LLM's opinion?* No: 75/100 is rules. The LLM part is a 1–5 anchored rubric.
   Stability is measured by running the same input N times (eval target: std-dev ≤ 3 points).
4. *What if Gemini is down?* Timeouts/429/5xx retry once with backoff, then Groq. If both fail → clear
   503 error. The parse-health results are already saved, so the user still sees them.
5. *How does two-column parsing work?* §3.1: gutter detection on line bounding boxes.
6. *How do you know the matching is any good?* `evals/resume/run.py`: labeled cases measure bullet recall,
   skill precision/recall, JD must-have P/R, tier accuracy, stability, guard interventions, latency/tokens.
7. *Security?* Strict JWT (no demo fallback), user-scoped queries, RLS, private bucket with signed
   URLs, magic-byte file checks, size/page caps, daily rate limits, no resume text in logs.
8. *Why is "listed_only" worth half?* Claiming a skill is weaker evidence than showing it used in a
   project, and recruiters read it the same way.
9. *Why do knockouts matter?* Research on ATS behaviour: eligibility filters (graduation year, CGPA,
   location) remove more candidates automatically than keyword scores do.
10. *What would you do next?* Run evals on the real model and tune prompts, then Celery for durability,
    pgvector to rank many saved JDs, and OCR for scanned PDFs.

---

## 9. Honest limitations (say these before an interviewer finds them)

- Background jobs live in the API process: a restart loses in-flight jobs (detected and shown as failed).
- Name redaction assumes the first line is the name. Unusual layouts can leak it.
- The skills taxonomy has about 100 entries; unknown skills still work but aren't normalised (no alias matching).
- Rule matching for "A **or** B" requirements needs *all* skills, so those go to the LLM judge.
- DOCX files have no page count (Word paginates at render time), so the length check uses word count only.
- The rate limit counts all rows created in 24 h, including failed ones.
- Eval numbers on the real model are pending until you run `python -m evals.resume.run`.

---

## 10. Running it

```bash
# Backend (from backend/)
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q                     # 107 tests, no database or API keys needed
ruff check .

# Local app without Supabase or API keys
set DATABASE_BACKEND=memory & set LLM_PROVIDER=fake & set SUPABASE_JWT_SECRET=<any 32+ char secret>
uvicorn app.main:app --port 8000
python scripts/mint_test_token.py <same secret>        # copy the token

# Frontend (from frontend/), in another terminal
set NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 & set NEXT_PUBLIC_E2E_ACCESS_TOKEN=<token>
npm run dev -- -p 3100        # open http://localhost:3100/dashboard/resume
npx playwright test           # E2E against that running app

# Real run: apply supabase/migrations/20261124000000_resume_v2.sql to your Supabase project,
# set the keys from .env.example in backend/.env, and remove the memory/fake variables.

# Evals (from backend/)
python -m evals.resume.run --fake --runs 1        # checks the harness, free
python -m evals.resume.run --out ../docs/evals/resume-v1.md   # real model, a few cents

# After changing a backend response model
python scripts/export_openapi.py && cd ../frontend && npm run gen:api
```

---

## 11. File map

```
backend/app/core/      auth.py (JWT) · db.py (user-scoped data layer) · errors.py · config.py
backend/app/llm/       client.py (validate/repair/fallback/log) · providers.py · fake_responses.py · prompts/*.v1.md
backend/app/resume/    api.py (routes) · service.py (upload) · jd.py · analysis.py · summary.py · schemas.py
backend/app/resume/pipeline/
    ingest.py  extract_pdf.py  extract_docx.py  document.py      <- getting text out
    contacts.py  sections.py  checks.py                          <- parse health
    redact.py  structure.py                                      <- AI structuring + grounding
    lint.py  taxonomy.py  guard.py  review.py  scoring.py        <- general review
    jd_parse.py  match.py  knockouts.py                          <- JD match
backend/app/resume/data/   section_aliases.yaml · skills_taxonomy.yaml · lint_words.yaml
backend/tests/resume/      unit + API tests (builders.py makes synthetic PDFs/DOCX in code)
backend/evals/resume/      cases.yaml (labeled) · run.py
supabase/migrations/       20261124000000_resume_v2.sql
frontend/src/lib/api/      client.ts · types.gen.ts (generated) · types.ts
frontend/src/features/resume/   hooks.ts · components/*
frontend/src/app/dashboard/resume/   page.tsx · [resumeId]/page.tsx · analysis/[analysisId]/page.tsx
frontend/e2e/              resume.spec.ts (Playwright)
.github/workflows/ci.yml   backend · frontend · e2e
```

---

## 12. Draft CV bullets (verify each, fill numbers from your real eval run)

- Built a resume screening pipeline (FastAPI, PyMuPDF, Supabase/Postgres with RLS) with layout-aware
  two-column parsing, 16 parse-health checks and evidence-cited JD matching across must/nice requirements
  and eligibility knockouts.
- Designed a truth guard that blocks AI rewrites from adding numbers, technologies or leadership claims
  (property-tested), plus PII redaction before every LLM call to reduce name-based bias.
- Built a schema-validated LLM layer (Pydantic structured output, repair retry, Gemini→Groq fallback,
  per-call latency/token logging, versioned prompts), cutting AI calls per analysis from 7 to 1–2.
- Evaluated on a labeled set: [N]% bullet recall, [N]% skill recall, score std-dev [X] points over
  repeated runs. Tested with 107 pytest tests, a Playwright E2E test and GitHub Actions CI.
