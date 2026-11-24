# Jadui Placement: AI Career Coach

![Stack](https://img.shields.io/badge/Stack-Next.js%20|%20FastAPI%20|%20Supabase-blue?style=for-the-badge)
![AI](https://img.shields.io/badge/LLM-Gemini%20|%20Groq-emerald?style=for-the-badge)

**Jadui Placement** is an AI career coach for students preparing for placements. The goal is one connected
loop: screen your resume (in general and against a job description), practise mock interviews, get an AI task
plan for your goal, track it on a dashboard, and ask a coach chat that knows all of it.

The project is being rebuilt pillar by pillar. Each pillar gets a research-backed plan, tests and a study guide.

| Pillar | Status |
|:---|:---|
| Resume screener (general review + JD match) | **Rebuilt (v2)** |
| Mock interviews | Legacy, being rebuilt next |
| AI goal-based task planner | Legacy, planned |
| Dashboard | Legacy, planned |
| Coach chat | Legacy, planned |

---

## Architecture

```
Next.js 14 (App Router, TypeScript for new code, React Query)
        |  Supabase session JWT on every request
FastAPI (Python 3.13)
  app/core     auth (JWT/JWKS), errors, user-scoped data layer
  app/llm      one LLM client: versioned prompts, schema validation, retry, fallback, call log
  app/resume   resume v2 pipeline, API at /api/v2
  modules/     legacy interview, mentor and system modules (replaced as each pillar is rebuilt)
        |
Supabase: Postgres with RLS, private Storage, Auth
```

---

## Resume Screener (v2)

The first pillar rebuilt from scratch (`backend/app/resume`, `frontend/src/features/resume`).

```
upload -> layout-aware text extraction -> 16 parse-health checks -> PII redaction
       -> LLM structuring + grounding check -> general review  or  JD match -> documented score
```

- **Deterministic first.** 75/100 of the general score is computed by rules; the LLM rates substance on an
  anchored 1-5 rubric. Every sub-score shows its formula in the UI.
- **Grounded AI output.** Every bullet the LLM extracts must exist in the original text; every requirement
  marked as met quotes the bullet that proves it.
- **Truth guard.** Suggested rewrites can rephrase but never add numbers, technologies, companies or
  leadership claims. Missing metrics become `[X]` placeholders plus coach questions.
- **Bias reduction.** Name and contact details are redacted before any LLM call.
- **Engineering.** Pydantic-validated LLM layer (repair retry, Gemini->Groq fallback, call logging,
  versioned prompts), user-scoped data access + Supabase RLS, content-hash caching, 107 backend tests,
  Playwright E2E, eval harness on labeled cases, GitHub Actions CI.

Study guide with design decisions and formulas: [docs/learn/resume-screener-guide.md](docs/learn/resume-screener-guide.md)

---

## Technology Stack

| Layer | Technology |
|:---|:---|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, React Query, Recharts |
| **Backend** | FastAPI, Pydantic v2, Uvicorn |
| **Database** | Supabase (Postgres with RLS, Storage, Auth) |
| **LLM** | Gemini (primary) + Groq (fallback), schema-validated structured output |
| **Quality** | pytest, Playwright, ruff, ESLint, eval harness, GitHub Actions CI |

---

## Getting Started

### Prerequisites
- Node.js 18+ and Python 3.13
- A Supabase project (apply the migrations in `supabase/migrations/`)
- API keys: `GEMINI_API_KEY` (and optionally `GROQ_API_KEY` for the fallback)

### Environment
- Backend: copy `.env.example` to `backend/.env`.
- Frontend: copy `frontend/.env.local.example` to `frontend/.env.local`.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # http://localhost:8000, health check: GET /health
pytest -q
```

No keys yet? Run with `DATABASE_BACKEND=memory LLM_PROVIDER=fake` to use an in-memory database and canned
AI answers.

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:3000
```
