# Resume Screener v2 — Research + Implementation Plan

**Status:** DRAFT for owner review. Nothing is built yet.
**Scope:** the resume pillar only (general review and JD match). Interviews, planner, dashboard and chat are out of scope here. They will *consume* this pillar's outputs later (§12).
**Related:** [`REVIEW.md`](../../REVIEW.md) §3 #4-7, §4.3. Those are the defects this plan replaces.

---

## 0. Summary

We rebuild the resume screener as a **staged, testable pipeline**:

```
upload → extract text (layout-aware) → parse-health checks → structure into a profile → general review / JD match → score → truth-guarded suggestions
```

Each stage is a pure function with its own tests. Deterministic code does everything that can be measured. The LLM does only what needs judgment, and its output is **schema-validated and grounded in the resume text**.

The differentiator, carried over from your CV Optimizer: **it never invents facts.** Suggested rewrites can't add numbers, technologies or claims that aren't in your resume. Where a metric is missing, the tool asks you a question ("How many users used this?") instead of making one up.

**LLM calls per run:**

| Action | Today | v2 |
|--------|-------|----|
| Upload + parse | 0 | 1 |
| General review | 7 | 1 |
| JD match | (not supported) | 1 parse (cached) + 1 judge |

---

## 1. Research findings → design principles

| # | Finding | Design consequence |
|---|---------|--------------------|
| 1 | Automated rejection by "ATS score" is mostly a myth. The main automated filters are **knockout questions** (eligibility such as work authorization or licenses). Keyword filters are used more for recruiter **search and sourcing** than for auto-rejection, and humans still make the call. ([Enhancv](https://enhancv.com/blog/does-ats-reject-resumes/), [ClearanceJobs](https://news.clearancejobs.com/2026/07/29/recruiters-reveal-ats-doesnt-kill-your-resume-its-overwhelming-volume/), [Huntr](https://huntr.co/blog/how-applicant-tracking-systems-work), [BetaNews](https://betanews.com/2025/11/10/study-debunks-viral-claim-that-ai-filters-out-most-job-applicants/)) | **Don't sell a fake "ATS score".** We report (a) **parse health**: can a parser read this file correctly? (b) a **JD match** score with a transparent formula. (c) **knockout risks**, shown prominently: graduation year, CGPA cutoff, location, notice period. Knockouts are what actually removes candidates. |
| 2 | Market leaders (Jobscan, Resume Worded) structure reports as: **searchability/parse checks** (contact info, headings, dates, job title), then **hard skills > education > title > soft skills** by weight, then measurable results and buzzwords. Resume Worded runs 20+ checks and line-by-line bullet feedback, for example "Only 2 of 14 bullets carry a number". ([Jobscan tutorial](https://jobscan.co/jobscan-tutorial), [Jobscan match report](https://www.jobscan.co/video-resume-match-report), [Resume Worded](https://resumeworded.com/), [Resume Worded score page](https://resumeworded.com/upload-resume)) | Match the users' mental model: a **parse-health section**, **hard-skill-weighted JD match**, **bullet-by-bullet feedback**. Beat them on **transparency** (show every formula), **evidence** (cite the bullet that proves each requirement) and **honesty** (no invented metrics). |
| 3 | PDF reading order is the #1 parsing failure. Text comes out in storage order, not reading order. Two-column resumes get scrambled by every library at default settings. The fix is geometric: extract blocks with coordinates, detect columns, then order the text. ([Artifex multi-column guide](https://artifex.com/blog/extracting-text-from-multi-column-pages-a-practical-pymupdf-guide), [parser benchmark](https://seanlikesdata.github.io/parser-bench/results/dashboard.html), [benchmark write-up](https://python.plainenglish.io/pymupdf-vs-pdfplumber-vs-pypdf-vs-pypdfium2-all-4-got-every-word-all-4-scrambled-one-page-d12054be37bd)) | Use **PyMuPDF `get_text("dict")`** for blocks and coordinates, plus our own column detection. **Keep line breaks** (today's bug). Warn the user when a multi-column layout is detected, and **show them the extracted text**, because that is what a parser sees. |
| 4 | Embedding-based screening shows strong **name-based race and gender bias** (UW study, >3M comparisons, 85% preference for white-associated names). ([UW News](https://www.washington.edu/news/2024/10/31/ai-bias-resume-screening-race-gender/), [Brookings](https://www.brookings.edu/articles/gender-race-and-intersectional-bias-in-ai-resume-screening-via-language-model-retrieval), [arXiv 2407.20371](https://www.arxiv.org/pdf/2407.20371)) | **Redact name and contact details before any scoring LLM call.** Contact details are extracted deterministically with regex, so the LLM never needs them. Document this in the README. It's a strong responsible-AI talking point, and it matches your "Responsible AI" certificate. |
| 5 | Skill matching research: taxonomy mapping (ESCO) + embeddings + an **LLM re-ranker/judge** works best. Bi-encoders are cheap pre-filters. ([CareerBERT](https://arxiv.org/pdf/2503.02056), [LLM ESCO matcher](https://arxiv.org/pdf/2307.03539), [JobSkape](https://arxiv.org/pdf/2402.03242), [IJCAI 2024](https://ijcai.org/proceedings/2024/1011.pdf)) | v2 uses an **alias taxonomy** (seeded from your CV Optimizer tag table) for exact matches, plus an **LLM evidence judge** for everything else. A resume has about 30 bullets, which fits in one call, so **embeddings aren't needed for v2**. They come later, for ranking many saved JDs (§13). |
| 6 | Gemini SDKs accept **Pydantic schemas directly** for structured output (`model_json_schema()` in, `model_validate_json()` out). JSON Schema is supported on all active models. ([Gemini structured output docs](https://ai.google.dev/gemini-api/docs/structured-output), [Google blog](https://blog.google/technology/developers/gemini-api-structured-outputs/)) | One `LLMClient.structured(schema=PydanticModel, …)` call, validated on return, with one repair retry. Replaces today's 3 ad-hoc JSON parsers. Use the **`google-genai`** SDK, not the legacy `google-generativeai`. |
| 7 | Groq **strict** structured outputs (constrained decoding) are only available on some models (docs name `openai/gpt-oss-120b`/`20b`). Other models are best-effort, and users report intermittent validation failures. ([Groq docs](https://console.groq.com/docs/structured-outputs), [HF forum](https://discuss.huggingface.co/t/groq-route-intermittently-returns-json-validate-failed-with-strict-structured-outputs/179097), [LangChain issue](https://github.com/langchain-ai/langchain/issues/34155)) | Groq is the **fallback** provider, and only with a strict-capable model. Still validate with Pydantic regardless. **Model names live in config.** Verify them against the live model pages when implementing; the search results showed several current Gemini names, so don't hardcode one. |

### Design principles (rules for every step below)
1. **Deterministic first, LLM second.** If it can be counted (numbers in bullets, headings, links, page count), code counts it.
2. **Every LLM output is schema-validated and grounded.** An extracted bullet must exist in the raw text. A cited evidence bullet ID must exist. A rewrite must pass the truth guard.
3. **Every score is a documented formula** that the UI can explain ("how is this calculated?").
4. **Never invent facts.** Ask the user for a missing metric; don't fabricate one.
5. **Honest framing.** The UI says what we simulate and what nobody can know (a company's real ATS configuration).
6. **Cheap and repeatable.** Results are cached by content hash, so the same resume + JD + prompt version gives the same result. Temperature is 0 for extraction and judging.

---

## 2. Feature spec

### MVP (this plan)

**A. Resume library**
- Upload a PDF or DOCX (≤5 MB, ≤3 pages). Keep multiple versions ("SDE v1", "Backend v2"). Rename, delete, download the original.

**B. Parse health ("what a parser sees")**
- Side-by-side view: the original file next to the **extracted text**.
- About 14 deterministic checks, each pass/warn/fail with a fix (§5.1). Examples: scanned PDF, garbled text, icon-font glyphs, two-column layout, contact info in header or footer, missing standard headings, unparseable dates, wrong length for experience level.

**C. Structured profile with human-in-the-loop**
- The resume is turned into sections: contact (regex), education (incl. CGPA and graduation year), experience, projects, skills, certifications, achievements. Every bullet gets a stable ID.
- The user can **review and correct** the extracted data before analysis. This is the same idea as your CV Optimizer's verified profile.

**D. General review**
- **Overall score with 5 sub-scores** (§6.1), each with "how calculated".
- **Bullet-by-bullet feedback.** Each bullet gets issue chips (no metric, weak verb, too long, pronoun, passive, buzzword, vague), a rubric rating, a **truth-guarded rewrite**, and **coach questions** for missing facts.
- Resume-level findings: skills listed but never shown in any bullet, repeated starting verbs, sections out of order, missing links (GitHub/LinkedIn/LeetCode for SDE roles).
- An optional "target role" input sharpens the relevance part of the review.

**E. JD match**
- Paste a JD. It's saved to a JD library and parsed into title, seniority, **must-haves vs nice-to-haves**, years, education, CGPA/graduation-year/location knockouts, and top keywords.
- **Requirement checklist:** each requirement is marked ✅ strong / 🟡 partial / ❌ missing, with **the quoted bullet that proves it**.
- **Match score + tier** with an **honesty gate** (§6.2). For example, below 40 the tool says "not a fit, don't stretch your resume", and the gaps are logged.
- **Knockout banner:** e.g. "JD requires graduation 2026, your resume says 2027".
- **Tailoring suggestions:**
  1. Keywords you *can* truthfully add, and where.
  2. Keywords you *can't* claim → added to the **gap list**.
  3. Suggested bullet order for this JD.
  4. Up to 5 bullet rewrites that mirror the JD's wording (guarded).
  5. A summary line (guarded).

**F. History and compare**
- Every analysis is saved. Re-run on a new version and see score deltas per sub-score.

**G. Outputs for other pillars**
- Writes `skill_gaps` rows (source = resume / JD) for the future planner and chat. The resume pillar doesn't build those features; it just exposes the data.

### Explicitly NOT in MVP (see §13)
- OCR for scanned PDFs (we detect them and explain instead).
- Generating a tailored PDF.
- Ranking many saved JDs (embeddings / pgvector).
- Celery/Redis workers.
- Recruiter-side bulk screening.

---

## 3. Architecture

### 3.1 Pipeline
```
                         ┌────────────── POST /resumes (multipart) ──────────────┐
                         ▼                                                        │
 [ingest]  validate magic bytes · size · pages → sha256 → Supabase Storage (private)
    │
 [extract] PDF: PyMuPDF dict → blocks(x,y) → column detection → ordered lines (newlines kept)
    │      DOCX: paragraphs + tables in order          → ExtractedDoc{text, lines, meta}
    │
 [checks]  deterministic parse-health checks           → list[Check]
 [contacts] regex: email/phone/LinkedIn/GitHub/LeetCode/portfolio
 [sections] heading detection (+ alias list)           → raw section spans
    │
 [redact]  remove name/contact lines                    → text for LLM
 [structure] LLM → ResumeProfile (Pydantic) → grounding check (each bullet ⊂ raw text)
    │                                                    → resume.status = ready
    │
    ├── POST /analyses {mode: general}
    │     [lint] deterministic bullet rules
    │     [review] LLM rubric per bullet + rewrites + coach questions (1 call)
    │     [guard] truth guard on every rewrite
    │     [score] formula §6.1                              → analysis.result
    │
    └── POST /analyses {mode: jd, jd_id}
          [jd_parse] LLM → JobRequirements (cached by jd text hash)
          [normalize] alias taxonomy on both sides
          [evidence] exact matches → LLM judge for the rest (cites bullet ids, validated)
          [knockouts] grad year / CGPA / location vs profile
          [tailor] keyword placement, reorder, guarded rewrites
          [score] formula §6.2 + tier + honesty gate       → analysis.result + skill_gaps
```

### 3.2 Jobs (async)
- Structuring and analysis take 5-20 s, which is too long to hold a request open on free hosting. So: `POST` creates a row with `status=queued`, returns **202** + id, and the frontend polls `GET` every 1.5 s.
- **v2 runner:** an in-process asyncio worker behind a small `JobRunner` interface (`enqueue(job_type, id)`). On startup, rows stuck in `running` for more than 5 min are marked `failed` and can be retried.
- **Upgrade path** (optional R13): swap the runner for **Celery + Redis** without touching the pipeline. Both are already on your skills list.

### 3.3 Backend layout (new code; old `modules/resume_ai` is deleted at R12)
```
backend/app/
  core/       config.py · auth.py (strict JWT) · db.py · errors.py · logging.py · rate_limit.py
  llm/        client.py (LLMClient, structured()) · providers/gemini.py · providers/groq.py
              · providers/fake.py (tests) · usage.py (llm_calls log) · prompts/ (versioned)
  jobs/       runner.py
  resume/
    api.py            # FastAPI router
    schemas.py        # all Pydantic models (§7)
    repository.py     # Supabase queries, always user-scoped
    service.py        # orchestration + job handlers
    pipeline/
      ingest.py  extract_pdf.py  extract_docx.py  layout.py  checks.py  contacts.py
      sections.py  redact.py  structure.py  lint.py  review.py  guard.py  scoring.py
      jd_parse.py  taxonomy.py  match.py  knockouts.py  tailor.py
    data/
      skills_taxonomy.yaml   # canonical skill → aliases, category (seed from CV Optimizer tags)
      action_verbs.txt  weak_phrases.txt  buzzwords.txt  section_aliases.yaml
backend/tests/resume/        # unit + API tests, LLM via fake provider/cassettes
backend/tests/fixtures/      # make_fixtures.py generates synthetic PDFs/DOCX
backend/evals/resume/        # golden set + run.py (real LLM, run manually)
supabase/migrations/         # SQL migrations (Supabase CLI)
```

### 3.4 Frontend layout
```
frontend/src/
  lib/api/client.ts            # fetch + Supabase token + error mapping (no Next.js proxy routes)
  lib/api/types.gen.ts         # generated from FastAPI OpenAPI (openapi-typescript)
  features/resume/
    hooks.ts                   # React Query: useResumes, useResume, useAnalysis (polling), useJds
    components/
      UploadDropzone.tsx  ParseHealthPanel.tsx  ExtractedTextView.tsx  ProfileEditor.tsx
      ScoreCard.tsx  ScoreExplainer.tsx  BulletFeedbackList.tsx  CoachQuestion.tsx
      JdInput.tsx  RequirementChecklist.tsx  KnockoutBanner.tsx  TailoringPanel.tsx
      GapList.tsx  VersionCompare.tsx
  app/dashboard/resume/
    page.tsx                         # library: resumes + JDs + recent analyses
    [resumeId]/page.tsx              # parse health + profile editor + "Analyze" (general / JD)
    analysis/[analysisId]/page.tsx   # results
```
New files are **TypeScript**. Next.js supports mixing TS and JS, so the rest of the app can migrate later. Types generated from OpenAPI prevent the response-shape bugs found in REVIEW §3 #3 and #7.

---

## 4. Data model (migration `0001_resume.sql`)

```sql
create extension if not exists pgcrypto;

create table public.resumes (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  title         text not null,                 -- "SDE v2"
  storage_path  text not null,                 -- resumes/{user_id}/{id}.pdf
  file_sha256   text not null,
  mime_type     text not null,
  page_count    int  not null,
  raw_text      text,                          -- ordered, newlines preserved
  extract_meta  jsonb not null default '{}',   -- columns, images, pua_chars, header/footer blocks
  checks        jsonb not null default '[]',   -- list[Check]
  contacts      jsonb not null default '{}',
  profile       jsonb,                         -- ResumeProfile (LLM, then user-editable)
  profile_edited boolean not null default false,
  status        text not null default 'queued' check (status in ('queued','processing','ready','failed')),
  error         text,
  created_at    timestamptz not null default now(),
  unique (user_id, file_sha256)                -- same file twice → reuse
);

create table public.job_descriptions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  title       text, company text,
  raw_text    text not null,
  text_sha256 text not null,
  parsed      jsonb,                           -- JobRequirements
  status      text not null default 'queued' check (status in ('queued','processing','ready','failed')),
  error       text,
  created_at  timestamptz not null default now(),
  unique (user_id, text_sha256)
);

create table public.resume_analyses (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references auth.users(id) on delete cascade,
  resume_id      uuid not null references public.resumes(id) on delete cascade,
  jd_id          uuid references public.job_descriptions(id) on delete set null,
  mode           text not null check (mode in ('general','jd')),
  target_role    text,
  status         text not null default 'queued' check (status in ('queued','running','done','failed')),
  error          text,
  input_hash     text not null,                -- sha256(profile json + jd hash + mode + prompt versions + model)
  overall_score  int,
  sub_scores     jsonb,
  result         jsonb,                        -- GeneralReview | JdMatch
  prompt_versions jsonb not null default '{}',
  model          text,
  created_at     timestamptz not null default now(),
  completed_at   timestamptz
);
create index on public.resume_analyses (user_id, created_at desc);
create index on public.resume_analyses (input_hash);

create table public.skill_gaps (               -- consumed later by planner/chat
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  skill       text not null,                   -- canonical name from taxonomy
  severity    text not null check (severity in ('must_have','nice_to_have','general')),
  source      text not null check (source in ('resume_review','jd_match','interview')),
  source_id   uuid not null,
  resolved_at timestamptz,
  created_at  timestamptz not null default now(),
  unique (user_id, skill, source, source_id)
);

create table public.llm_calls (                -- cost/latency/debug log
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  purpose text not null, provider text not null, model text not null, prompt_version text not null,
  input_tokens int, output_tokens int, latency_ms int, ok boolean not null, error text,
  created_at timestamptz not null default now()
);

-- RLS: owner-only on every user table
alter table public.resumes          enable row level security;
alter table public.job_descriptions enable row level security;
alter table public.resume_analyses  enable row level security;
alter table public.skill_gaps       enable row level security;
alter table public.llm_calls        enable row level security;
create policy own_resumes  on public.resumes          for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy own_jds      on public.job_descriptions for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy own_analyses on public.resume_analyses  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy own_gaps     on public.skill_gaps       for all using (user_id = auth.uid()) with check (user_id = auth.uid());
-- llm_calls: no user policy (backend-only)
```
**Storage:** a private bucket `resumes`, with the path prefixed by `user_id`. Downloads use short-lived signed URLs.

**Backend access:** the repository layer **always** filters by `user_id` taken from the verified JWT. No function accepts a `user_id` from the request body. RLS is the second line of defense.

---

## 5. Deterministic components

### 5.1 Parse-health checks (`checks.py`)
| id | Check | Fail / warn rule | Fix shown to user |
|----|-------|------------------|-------------------|
| `text_extractable` | Text exists | <200 chars → **fail** (likely scanned) | "Export from Word/Docs/LaTeX, not a scan." |
| `garbled` | Readable characters | alphanumeric ratio <0.45, or `(cid:NN)` tokens → **fail** (rule from CV Optimizer `build.py`) | "Font encoding issue; re-export with standard fonts." |
| `icon_glyphs` | Icon fonts | Unicode private-use chars present → **warn** | "Icons (e.g. FontAwesome) become junk for parsers; use text labels." |
| `columns` | Layout | >1 text column detected → **warn**; show extracted order | "Single column is safest; check the extracted text below." |
| `header_footer_contact` | Contact in header/footer | email/phone only in top/bottom 6% band → **warn** | "Some parsers skip headers; put contact in the body." |
| `contact_email` / `contact_phone` | Present | missing → **fail** / **warn** | |
| `links` | LinkedIn, GitHub (+ LeetCode/portfolio for SDE) | missing GitHub for tech role → **warn** | |
| `headings` | Education, Experience or Projects, Skills | each missing → **warn**; non-standard names ("My Journey") → **warn** | "Use standard headings." |
| `dates` | Parseable dates | entries without parseable dates → **warn** | "Use 'Jun 2025 – Aug 2025'." |
| `chronology` | Newest first | out of order → **warn** | |
| `length` | Pages vs experience | >1 page with <3 yrs, or >2 pages → **warn** | |
| `word_count` | Density | <250 or >1000 words → **warn** | |
| `tables_images` | Tables/images | images or DOCX tables holding text → **warn** | |
| `filename` | File name | no name-like token ("final_v3.pdf") → **info** | "Use Firstname_Lastname_Resume.pdf." |

### 5.2 Bullet lint (`lint.py`)
Each rule is a pure function `(bullet, context) -> Issue | None`. All rules are table-tested.

| Rule | Detects |
|------|---------|
| `no_metric` | No number, %, x, ₹/$, or count word |
| `weak_start` | First token not in `action_verbs.txt`, or a weak opener ("Responsible for", "Worked on", "Helped") |
| `pronoun` | I / me / my / we / our |
| `passive` | `(was\|were\|is\|are\|been\|being) \w+(ed\|en)\b( by)?` |
| `length` | <8 or >32 words |
| `buzzword` | "passionate", "hardworking", "synergy", "go-getter", … (`buzzwords.txt`) |
| `vague` | "various", "etc.", "multiple things", "many" with no object |
| Resume-level: `repeated_verb` | Same opening verb used >3 times |
| Resume-level: `unsupported_skill` | A skill in the Skills section that never appears in any bullet ("show it or drop it") |

### 5.3 Taxonomy (`skills_taxonomy.yaml`)
- **Seed:** your CV Optimizer tag table (`reference.md` §1-2) plus about 150 common tech skills.
- **Format:**
  ```yaml
  PostgreSQL: {aliases: [postgres, postgresql, psql], category: database}
  ```
- `normalize(text) -> set[canonical]` uses whole-word alias matching. That fixes the "git inside digital" class of bugs and is already tested in the current repo.
- Unknown skills from the LLM are kept as-is (lowercased) and logged, so the taxonomy can grow.

---

## 6. Scoring (documented in the README; shown in the UI)

### 6.1 General score (0-100)
| Sub-score | Max | Formula |
|-----------|-----|---------|
| **Parse health** | 20 | 20 − 6×fails − 2×warns (min 0) |
| **Impact** | 25 | 15 × min(1, quantified_bullets / (0.5 × bullets)) + 10 × action_verb_ratio |
| **Clarity** | 15 | 15 × (bullets with no length/pronoun/passive/buzzword/vague issue) / bullets |
| **Completeness** | 15 | 3 points each: contact, education, skills, experience-or-projects, links |
| **Substance** (LLM) | 25 | mean over bullets of (specificity + technical_depth + outcome) on a 1-5 anchored rubric → scaled to 25; −2 per `unsupported_skill` (max −6) |

- 75 of the 100 points are **deterministic**. Only Substance depends on the LLM, at temperature 0 with anchored rubric definitions in the prompt.
- **Stability target:** the same input over 3 runs varies by ≤3 points (checked in evals).

### 6.2 JD match score (0-100), adapted from your CV Optimizer fit rubric
| Component | Max | Formula |
|-----------|-----|---------|
| **Must-have coverage** | 45 | 45 × Σ(strong=1, partial=0.5, listed_only=0.5, missing=0) / must_haves |
| **Nice-to-have coverage** | 15 | same over nice-to-haves (15 if the JD lists none) |
| **Evidence depth** | 15 | 15 × (must-haves backed by an experience/project bullet, not just the skills list) / matched must-haves |
| **Experience fit** | 10 | 10 if years/seniority fit; 5 if within one level or unknown; 0 if far off |
| **Role alignment** | 5 | LLM judge 0-5: does the resume's direction match the title? |
| **Knockouts** | 10 | 10 none; 5 unknown; 0 any conflict (and always shown as a banner) |

**Tiers / honesty gate:**

| Score | Tier | What the UI says |
|-------|------|------------------|
| ≥80 | **Strong fit** | Apply. Tailor the top bullets. |
| 60-79 | **Good fit** | Apply after the tailoring suggestions. |
| 40-59 | **Stretch** | Apply with the base resume. Gaps are logged; don't over-tailor. |
| <40 | **Not a fit yet** | Don't stretch the resume. Here's what to learn. |

---

## 7. Key schemas (Pydantic, `resume/schemas.py`)

```python
class Bullet(BaseModel):
    id: str                       # "exp0.b2" — stable within a resume version
    text: str
    section: Literal["experience","projects","achievements","summary","other"]
    grounded: bool = True         # passed the "exists in raw text" check

class Entry(BaseModel):           # one job or one project
    id: str; title: str; org: str | None; start: str | None; end: str | None
    tech: list[str] = []; bullets: list[Bullet]

class Education(BaseModel):
    institution: str; degree: str | None; field: str | None
    grad_year: int | None; cgpa: float | None; cgpa_scale: float | None

class ResumeProfile(BaseModel):
    headline: str | None; summary: str | None
    education: list[Education]; experience: list[Entry]; projects: list[Entry]
    skills: list[str]; certifications: list[str]; achievements: list[Bullet]
    location: str | None

class Check(BaseModel):
    id: str; status: Literal["pass","warn","fail","info"]; message: str; fix: str | None

class BulletReview(BaseModel):
    bullet_id: str
    issues: list[Literal["no_metric","weak_start","pronoun","passive","length","buzzword","vague","low_depth","unclear_outcome"]]
    specificity: conint(ge=1, le=5); technical_depth: conint(ge=1, le=5); outcome: conint(ge=1, le=5)
    rewrite: str | None            # passed the truth guard, may contain [X] placeholders
    coach_questions: list[str]     # "How many users used this feature?"
    guard_notes: list[str] = []    # what the guard removed, shown in dev mode

class Requirement(BaseModel):
    id: str; text: str; kind: Literal["must","nice"]; skills: list[str]  # canonical

class Knockout(BaseModel):
    type: Literal["grad_year","cgpa","location","notice","work_auth","degree","other"]
    jd_value: str; resume_value: str | None
    status: Literal["ok","conflict","unknown"]

class JobRequirements(BaseModel):
    title: str; company: str | None; seniority: Literal["intern","entry","mid","senior","unknown"]
    min_years: float | None; requirements: list[Requirement]
    knockouts: list[Knockout]; keywords: list[str]; responsibilities: list[str]

class RequirementMatch(BaseModel):
    requirement_id: str
    status: Literal["strong","partial","listed_only","missing"]
    evidence_bullet_ids: list[str]  # validated: must exist in the profile
    reason: str
```

---

## 8. Truth guard (`guard.py`): the core differentiator

**Input:** the original bullet, the proposed rewrite, and the resume-wide evidenced entities.

**Rules:**
1. **Numbers:** every number in the rewrite must appear in the original bullet. Otherwise it's replaced with `[X]` and a coach question is added.
2. **Technologies:** every taxonomy skill in the rewrite must appear in the original bullet, or in the same entry's `tech` list. Otherwise it's removed, or the suggestion is flagged `requires_confirmation: "Only add Docker if you actually used it here."`
3. **Proper nouns:** capitalized tokens not in the original bullet or entry (company names, product names) → rejected.
4. **Claim inflation:** verbs from a "seniority-inflation" list (led, architected, spearheaded) are allowed only if the original already implies ownership. Otherwise they're downgraded and flagged.
5. **No fix possible:** if a rewrite can't be fixed, it's dropped and only the coach questions are kept.

**Tests:** table tests plus property-style tests (random original/rewrite pairs, asserting that rewrite entities ⊆ allowed entities).

**Metric** tracked in evals: **guard rejection rate**, plus **post-guard hallucination rate**, which must be 0.

---

## 9. Privacy, fairness, abuse

- **Redaction before LLM:** the first-line name, email, phone, address and URLs are removed or replaced with tokens (`[NAME]`, `[EMAIL]`). Contacts come from regex, so the LLM never needs them.
- **Owner-only access:** private storage, signed URLs, RLS, user-scoped repository functions, and an explicit delete (file + rows).
- **Rate limit:** e.g. 15 analyses and 10 uploads per user per day, enforced by counting rows (no Redis needed). Configurable.
- **Input caps:** 5 MB, 3 pages, JD ≤ 15k chars, profile text sent to the LLM ≤ 12k chars.
- **No resume content in logs.** Only IDs, timings and token counts.

---

## 10. API (mounted at `/api/v2` until the switchover in R12)

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/resumes` | multipart `file`, `title` → **202** `{id, status}`; same sha256 → returns the existing row |
| `GET` | `/resumes` | list (no raw_text) |
| `GET` | `/resumes/{id}` | full: status, checks, contacts, extract_meta, raw_text, profile |
| `PATCH` | `/resumes/{id}/profile` | user corrections → `profile_edited=true` |
| `GET` | `/resumes/{id}/file` | signed URL |
| `DELETE` | `/resumes/{id}` | file + rows |
| `POST` | `/jds` | `{raw_text, title?, company?}` → **202** |
| `GET` | `/jds`, `/jds/{id}` | |
| `DELETE` | `/jds/{id}` | |
| `POST` | `/analyses` | `{resume_id, mode, jd_id?, target_role?}` → **202**; cache hit → **200** with the existing analysis |
| `GET` | `/analyses/{id}` | status + result |
| `GET` | `/analyses` | `?resume_id=&mode=` |
| `GET` | `/resume/summary` | for the future dashboard: latest scores, top gaps, counts |

**Errors** use one shape: `{error: {code, message, details?}}`. Examples: `file_too_large`, `unsupported_type`, `scanned_pdf`, `rate_limited`, `llm_unavailable`, `not_found`.

---

## 11. Step-by-step implementation

Each step ends with **acceptance criteria** and is committed separately. The estimates are focused working days.

### R0 — Prep (0.5 d)
1. Commit the current state; tag `pre-rebuild`. Create branch `feat/resume-v2`.
2. Backend: create a fresh venv. Pin deps in `requirements.txt`. Add `requirements-dev.txt` (pytest, pytest-asyncio, ruff, respx). Add `PyJWT`, `pymupdf`, `google-genai`, `tenacity`, `pyyaml`, `rapidfuzz`. File-type detection is a small hand-written magic-byte check, so no `python-magic` dependency.
3. Add `ruff` config and `pytest.ini`. Get the existing parser tests running.
4. Frontend: `npm i`. Add `typescript`, `@tanstack/react-query`, `openapi-typescript`. Add `tsconfig.json` with `allowJs: true`.

**✅ Done when:** `pytest` and `npm run build` both pass on a clean clone.

### R1 — Foundation the resume pillar needs (1.5 d)
1. `core/auth.py`:
   - Verify the Supabase JWT (check whether your project uses HS256 or asymmetric/JWKS keys, and support that).
   - **No demo fallback:** a missing or invalid token → 401.
   - `CurrentUser` dependency.
2. `core/errors.py` (error shape), `core/logging.py` (JSON logs + request ID), `core/config.py` (models, limits, CORS from env, actually used).
3. Install the Supabase CLI. Create `supabase/migrations/0001_resume.sql` (§4) and the storage bucket. Apply it to your project.
4. `core/db.py` client plus a repository pattern with user-scoped helpers.

**Tests:** auth (valid, expired, missing, wrong signature); repository never returns another user's row (2 users).

**✅ Done when:** `GET /api/v2/resumes` with no token → 401, with a token → `[]`.

### R2 — LLM client (1 d)
1. `LLMClient.structured(schema, prompt_name, variables, temperature=0, user_id)`, which:
   - renders the versioned prompt from `llm/prompts/`
   - calls the primary provider (Gemini via `google-genai`, Pydantic schema)
   - validates; on `ValidationError`, does **one repair retry** that includes the error message
   - falls back to Groq (strict-capable model) on timeout or 5xx
   - times out at 30 s and retries with `tenacity` (2 tries, exponential backoff)
   - logs every attempt to `llm_calls`
2. `providers/fake.py`: returns fixture JSON per `prompt_name`. Used by all tests.
3. Model names come only from env/config (`LLM_PRIMARY_MODEL`, `LLM_FALLBACK_MODEL`). Pick the current Flash-tier Gemini and a strict-capable Groq model from the live docs.

**Tests:** validation retry path, fallback path, timeout path (respx-mocked HTTP), usage logging.

**✅ Done when:** a script call returns a validated Pydantic object from the real API, and the `llm_calls` row is written.

### R3 — Ingest + layout-aware extraction (1.5 d)
1. `ingest.py`:
   - magic bytes: `%PDF-` for PDF, `PK\x03\x04` + `word/document.xml` for DOCX
   - size and page caps; sha256
   - upload to storage; insert row; enqueue `process_resume`
2. `extract_pdf.py` with PyMuPDF `page.get_text("dict")`:
   - collect blocks/lines with bbox
   - `layout.py`: detect columns via an x-histogram gap (gutter) over line start positions; order the text left column then right, top to bottom
   - record `columns`, `images`, private-use char count, `(cid:` count, and which text sits in the header/footer bands
   - **keep `\n` between lines**
3. `extract_docx.py`: paragraphs and table cells in **document order**, by walking the XML body.
4. `tests/fixtures/make_fixtures.py` generates synthetic resumes with PyMuPDF's own writer:
   - single-column, two-column, icon-glyph, image-only ("scanned"), contact-in-header
   - DOCX with a skills table
5. `jobs/runner.py`: asyncio worker, `JobRunner` interface, stale-job recovery on startup.

**Tests:** for every fixture, the expected reading order (golden text snapshot), the column count, and the meta flags.

**✅ Done when:** the two-column fixture extracts in correct reading order, and newlines are preserved.

### R4 — Parse-health checks, contacts, sections (1 d)
1. `contacts.py`: regex for email, Indian and international phone formats, linkedin.com/in, github.com, leetcode.com, generic portfolio URL.
2. `sections.py`: heading detection with `section_aliases.yaml` (e.g. "Work Experience", "Professional Experience", "Internships" → experience). Uses line-level signals: short line, all caps or title case, followed by content.
3. `checks.py`: all of §5.1, each check a pure function.
4. The `process_resume` job now stores `checks`, `contacts`, and section spans.

**Tests:** table tests per check; fixtures produce the expected pass/warn/fail sets.

**✅ Done when:** uploading the fixtures through the API yields the expected checks in `GET /resumes/{id}`.

### R5 — Structuring + grounding + user edits (1.5 d)
1. `redact.py`: replace contacts and the name line with tokens.
2. Prompt `resume.structure.v1`: "extract, don't rewrite; copy bullet text verbatim; null if absent". Schema = `ResumeProfile`.
3. Grounding:
   - each bullet must fuzzy-match a span in the raw text (normalized whitespace, `rapidfuzz` partial ratio ≥ 90), otherwise `grounded=false` and it's excluded from scoring
   - education grad_year and CGPA are re-checked by regex against the raw text
4. Assign stable bullet IDs (`exp{i}.b{j}`, `proj{i}.b{j}`).
5. `PATCH /resumes/{id}/profile`: validated edits; bullets keep their IDs.
6. `resume.status = ready`.

**Tests:** cassette-based structure test; the grounding test injects a fake hallucinated bullet and expects it flagged; PATCH validation.

**✅ Done when:** a real upload of your own resume (locally, not committed) gives a correct profile with 0 ungrounded bullets.

### R6 — General review (2 d)
1. `lint.py`: all §5.2 rules plus resume-level rules.
2. Prompt `resume.review.v1`: one call with all grounded bullets (IDs + text), the lint issues, and the optional target role. It returns `list[BulletReview]`. The prompt contains the anchored 1-5 rubric definitions and the rule "never add numbers/tools not present; ask a coach question instead".
3. `guard.py`: §8, applied to every rewrite.
4. `scoring.py`: §6.1, returning sub-scores **plus an explanation string per sub-score** for the UI.
5. `POST /analyses` (general): compute `input_hash`; if it's cached, return the existing analysis; otherwise create a row and enqueue. Apply the rate limit.
6. Write `skill_gaps` rows only for `unsupported_skill` findings (severity `general`).

**Tests:** lint tables, guard tables + property tests, scoring tables (hand-computed expected values), cache-hit test, rate-limit test, end-to-end job with the fake LLM.

**✅ Done when:** analyzing a fixture returns a complete result. Re-posting the same request returns the cached analysis. No rewrite contains a number missing from its original.

### R7 — JD library + parsing (1 d)
1. `POST /jds` → hash; reuse if present → enqueue `parse_jd`.
2. Prompt `jd.parse.v1` → `JobRequirements`:
   - split must vs nice using section cues ("Requirements/Qualifications" vs "Preferred/Nice to have/Bonus")
   - extract knockouts (graduation year, CGPA, location/on-site, notice period, work authorization)
3. Deterministic post-processing:
   - normalize requirement skills via the taxonomy
   - regex-verify that numbers in knockouts (CGPA, years) appear in the JD text
4. Fixtures: 6 public JDs (backend intern, SDE intern, frontend, data/ML, QA automation, DevOps). Use public postings, or rewrite them in your own words.

**Tests:** cassette tests per fixture; knockout regex verification.

**✅ Done when:** the 6 JD fixtures parse with must/nice split and knockouts that match a hand-written label file.

### R8 — JD match + tailoring (2 d)
1. `match.py`:
   1. Exact pass: requirement skills ∩ bullet skills → `strong` (if in an experience/project bullet) or `listed_only` (skills section only).
   2. LLM judge (`match.judge.v1`, one call) for the rest *and* for non-skill requirements ("built REST APIs used in production"). Input: requirements + all grounded bullets with IDs. Output: `RequirementMatch` list, plus role alignment 0-5.
   3. Validate that every cited bullet ID exists, otherwise downgrade to `missing`.
2. `knockouts.py`: compare graduation year, CGPA (normalize scales: 8.8/10 vs %), location (on-site city vs resume location; unknown when absent) → `ok/conflict/unknown`.
3. `tailor.py` (`match.tailor.v1`, optionally the same call as the judge if the token budget allows):
   - keyword placement only where evidence exists
   - bullet reorder by relevance
   - ≤5 rewrites + a summary line, **all through the guard**
   - missing must-haves → gap list
4. `scoring.py`: §6.2 + tier + honesty-gate message.
5. Write `skill_gaps` (`must_have` / `nice_to_have`, source `jd_match`).

**Tests:**
- **Monotonicity:** adding a bullet that proves a missing must-have raises the score; adding a knockout conflict lowers it.
- Fabricated evidence IDs are rejected.
- Scoring tables.

**✅ Done when:** for your own resume against the 4 JDs in your CV Optimizer (local only), the tier is within one band of your CV Optimizer `tailor.py` fit score, and every ✅ cites a real bullet.

### R9 — Frontend (3 d)
1. `lib/api/client.ts`: attaches the Supabase access token, maps the error shape, sets the base URL from env. Generate `types.gen.ts` from `/openapi.json` (npm script `gen:api`).
2. React Query provider. `useAnalysis(id)` polls until `done`/`failed`.
3. Pages and components from §3.4:
   - **Library:** resume cards (title, date, status, last scores), JD list, "New analysis" dialog.
   - **Resume page:** `ParseHealthPanel` (checks grouped fail → warn → pass, each with a fix), `ExtractedTextView` (side-by-side with a PDF preview via the signed URL), `ProfileEditor` (edit/confirm sections), "Analyze" buttons.
   - **Analysis (general):** `ScoreCard` + `ScoreExplainer` popovers, `BulletFeedbackList` (original → issue chips → rewrite with [X] placeholders highlighted → coach questions → copy button), resume-level findings.
   - **Analysis (JD):** `KnockoutBanner`, tier + honesty message, `RequirementChecklist` (requirement · must/nice · status · quoted evidence, clickable to the bullet), `TailoringPanel`, `GapList`.
   - Honest copy: one line under the score: "Simulated. No tool can see a company's real ATS settings; knockouts and recruiter search matter most."
4. Empty, loading, error and rate-limited states. Mobile layout.
5. Remove the old resume UI from navigation (files are deleted in R12).

**✅ Done when:** you can go from upload to parse health to profile edit to general review to a JD match in the browser against the real backend, with no console errors.

### R10 — Versions and compare (0.75 d)
1. `VersionCompare`: pick 2 analyses of the same mode (and the same JD for JD mode) → table of sub-score deltas, plus new/resolved issues.
2. "Re-analyze with latest version" shortcut on the analysis page.

**✅ Done when:** uploading an improved fixture shows positive deltas on the sub-scores that changed.

### R11 — Evals (1.5 d)
1. `backend/evals/resume/`:
   - 10 **synthetic** resumes (varied quality, layouts, fresher vs experienced) + the 6 JDs
   - hand labels: sections, bullet count, skills, must-haves, expected tier band
2. `python -m evals.resume.run` (real LLM) reports:
   - section and bullet extraction recall
   - skill extraction precision/recall vs labels
   - JD must-have precision/recall
   - tier accuracy (within one band)
   - **score stability** (3 runs, std dev)
   - **post-guard hallucination rate** (target 0)
   - average latency and tokens per analysis
3. Save the report to `docs/evals/resume-v1.md`. Tune prompts → bump prompt versions → re-run.
4. Your real resumes and JDs from CV Optimizer go in a **gitignored** `evals/resume/private/` folder for local runs only.

**✅ Done when:** a committed eval report with real numbers exists. These numbers become your CV metrics.

### R12 — E2E, CI, docs, switchover (1.5 d)
1. Playwright E2E with a seeded test user and fake-LLM mode on the backend (`LLM_PROVIDER=fake`): upload fixture → see parse health → run general → see score → run JD → see checklist.
2. GitHub Actions:
   - **backend:** ruff + pytest
   - **frontend:** lint + `tsc --noEmit` + build
   - **E2E:** Playwright against both, in fake-LLM mode
3. **Switchover:**
   - mount the router at `/api/resume*` paths, drop `/v2`
   - **delete** `backend/modules/resume_ai/`, `frontend/src/app/api/resume/`, `features/resume/ResumeUpload.jsx`, `ResumeResults.jsx`, the old resume page code, and the tests that targeted the old modules
   - point the dashboard's resume stat card at `GET /resume/summary`, a minimal patch until the dashboard phase
4. README "Resume Screener" section: pipeline diagram, both scoring formulas, truth guard, redaction and bias note, eval results table.
5. Propose updated **CV Optimizer** bullets for Jadui (draft only; you verify and mark them `verified`).

**✅ Done when:** CI is green, the old resume code is gone, and the README matches the code exactly.

**Total: ≈ 18-19 focused days.**

---

## 12. How other pillars will use this (interfaces only, built later)

| Pillar | Reads |
|--------|-------|
| **Planner** | `skill_gaps` (unresolved, ordered by severity) + the latest `resume_analyses.sub_scores` |
| **Interview** | `resume.profile` (projects/bullets to ask about) + `job_descriptions.parsed` (JD-based interview) |
| **Dashboard** | `GET /resume/summary` |
| **Chat** | a `get_latest_analysis` tool → a compact summary of the latest general + JD analysis |

---

## 13. Later / optional
- **R13 Celery + Redis worker:** swap the `JobRunner`. Gives a real Redis/Celery bullet; needs hosted Redis (e.g. a free tier).
- **R14 JD library ranking:** pgvector embeddings of requirements and bullets to rank *all* saved JDs by fit ("which of these 20 jobs fit me best?"). This is where embeddings genuinely earn their place.
- **R15 OCR** for scanned PDFs (Tesseract or a vision model) behind a flag.
- **R16 Tailored PDF export:** reuse CV Optimizer's `render.py`/LaTeX approach to build a one-page tailored resume from accepted suggestions.
- **R17 ESCO mapping** for the taxonomy (standard occupation/skill IDs).

---

## 14. Decisions needed from you before R0

1. **Job runner:** in-process asyncio first and Celery later (recommended), or Celery + Redis from day 1?
2. **Primary LLM:** Gemini Flash-tier primary with Groq fallback (recommended), or Groq primary for speed?
3. **TypeScript for new frontend files:** yes (recommended; it's on your CV as "working"), or stay JS?
4. **Your resumes and JDs for local evals:** OK to use the PDFs and `jd.md` files from `CV Optimizer/applications/` in a gitignored folder?

---

## 15. CV impact (honest, only after R12)

You'll be able to defend bullets like the drafts below. The numbers come from the R11 eval report:

- "Built a layout-aware resume parsing pipeline (PyMuPDF column detection, 14 parse-health checks) and a JD-matching engine that cites evidence for every requirement; evaluated on a labeled set with N% skill-extraction recall and score variance ≤ X points."
- "Designed a truth guard that blocks fabricated metrics and technologies in LLM rewrites (0% post-guard hallucination on eval set) and redacts PII before model calls to reduce name-based bias."
- "Schema-validated LLM layer (Pydantic structured outputs, provider fallback, retries, per-call cost/latency logging) cutting LLM calls per analysis from 7 to 2."

**Note:** several current Jadui bullets in `CV Optimizer/profile/projects/jadui-placement.json` describe things the code doesn't do:
- Vapi WebRTC is unused
- there are no Pydantic output schemas
- there's no token-pool rotation
- the "660 lines" analyzer is now 218 lines
- TypeScript and Radix UI aren't used

They're marked `verified: true`. Consider marking them unverified until the rebuild makes them true.
