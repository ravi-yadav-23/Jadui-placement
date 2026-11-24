# Jadui Placement — Full Project Review (2026-11-24)

> **Status (2026-11-25):** the resume screener is rebuilt (v2), and the Phase 0 cleanup is done: admin/TPO
> panel, workshops, student dossiers, GitHub PR review and GitHub profile analytics are deleted, with unused
> packages and stale docs. The legacy interview, mentor and system modules stay until their pillars are
> rebuilt. File references below describe the code as it was on 2026-11-24.

This report replaces the old audits in the parent folder (`a.txt`, `report.txt`, `cleanup_manifesto.md`, `code_audit_report.md`). Those describe files that no longer exist and an earlier version of the product.

Every finding below was checked by reading the code. File references are relative to `agentic-ai-career-coach/`.

---

## 1. Verdict in one paragraph

The project is a set of features that were **ported from other repos** (HireLens, PulseAI, profile-summary-for-github) and then **wrapped in a second layer of glue code** while the product direction kept changing (TPO tool, then admin + student, now a personal career coach). The result:

- Most of the "AI" is **string templates**: the roadmap, daily plan, interview feedback for voice sessions, "resume boosters" and the fallback chat.
- The features that do call an LLM are **disconnected from each other**. The chat never actually receives your data (it's broken, see §3).
- The UI shows **fabricated numbers** in several places: mock progress, fake interview history, invented trend charts, fake streak.
- Auth is **effectively off**: no token means you're treated as a shared demo user, and the admin panel has a hardcoded bypass.

The good news: the stack is fine (Next.js + FastAPI + Supabase), and the codebase is only about 12k lines. That's small enough to rebuild around the new scope in a few focused phases, not a full restart.

---

## 2. The new scope (what we are building)

| # | Pillar | Must do |
|---|--------|---------|
| 1 | **Resume screening** | (a) General review (ATS, structure, impact, wording). (b) **Match against a pasted JD**: match score, missing skills or keywords, tailored bullet rewrites. |
| 2 | **Mock interviews** | Built from a role, a JD and/or the user's resume. Turn-by-turn, with follow-ups, per-answer scoring and a saved final report. Text first, voice optional. |
| 3 | **AI task planner** | The user sets a goal (role, target date, hours/week). AI generates a dated plan of milestones, weeks and daily tasks, linked to real gaps. Replans as progress is made. |
| 4 | **Dashboard** | Only real data, computed on the server from real tables, using **one** readiness formula. |
| 5 | **AI chat (coach)** | Grounded in the user's profile, goal, resume analyses, interview results and tasks. Can also *act*: create or reschedule tasks, start an interview. |

**Out of scope, to delete:** the admin/TPO panel, workshops, student dossiers, hiring simulation, GitHub PR review and repo architecture analysis. GitHub profile stats can return later as an optional data source, but they are not core.

---

## 3. Top 15 things that are broken right now

These are concrete defects, not style issues, ordered by impact.

| # | Area | What's wrong | Where |
|---|------|--------------|-------|
| 1 | **AI Chat** | `authHeader` is used inside `fetchSystemState()` and `callBackendMentor()` but is only defined inside `POST()`, so both throw `ReferenceError`. The first is silently swallowed; the second makes every backend-mentor call fall back to the template reply. | `frontend/src/app/api/mentor/chat/route.js:15`, `:264` |
| 2 | **AI Chat** | Backend URLs are missing the `/api` prefix (`/system/state`, `/resume/history`, `/interview/history`, `/mentor/chat`), so every one of them returns 404. | `mentor/chat/route.js:13`, `:78-79`, `:261` |
| 3 | **AI Chat** | The UI sends `{system_prompt, message, history}`, but the route reads `body.context`, which is never sent. The chat always runs as `demo-user` with an empty context, and the client's `system_prompt` is ignored. **The "context-aware mentor" has never had context.** | `features/chat/ChatInterface.jsx:84-88` vs `route.js:294-295` |
| 4 | **Resume** | The parser runs `normalize_space()`, which **collapses every newline**, before the text is stored. The section parser then splits on newlines, so section detection effectively never works on real uploads. The tests pass only because they feed in hand-written text that still has newlines. | `backend/modules/resume_ai/parser.py:40,52,75` → `section_parser.py:68` |
| 5 | **Resume** | The insert payload contains `weaknesses` and `recommended_roles`, but `schema.sql` has neither column. Both the main insert and the "fallback" insert fail, and the error is swallowed with `print()`. **Results are probably never saved**, unless your live DB has drifted from `schema.sql`. | `resume_ai/services.py:21-40, 136-155` vs `deployment/schema.sql:48-66` |
| 6 | **Resume** | There is no JD support at all. The UI's "Target role" text is sent as `jdText` and then used as `role_target`. | `ResumeUpload.jsx:45`, `api/resume/analyze/route.js:17,57` |
| 7 | **Resume** | After analysis, the UI dispatches `analyzeData.analysis`, which doesn't exist (the route returns a flat object), so `resumeData` becomes `undefined`. | `features/resume/ResumeUpload.jsx:56,69` |
| 8 | **Interview** | If the LLM returns empty or invalid JSON, `extract_json_from_llm_response` returns `{}` without raising, so the fallback evaluator never runs and the answer is **scored 0/0/0**. | `interview_ai/services.py:209-217` |
| 9 | **Interview** | Voice sessions: every speech-recognition fragment becomes a separate "user" message, and the feedback route maps the *i-th fragment* to *question i*. Answers get scored against the wrong questions, and the loop stops once there are more fragments than questions. | `dashboard/interview/page.jsx:152-157`, `api/interview/feedback/route.js:43-58` |
| 10 | **Interview** | The per-answer `gaps` and `strengths` the LLM returns are **never saved** (no columns exist for them), so syncing interview gaps to the profile always receives an empty list. | `interview_ai/services.py:243-254`, `routes.py:84-90` |
| 11 | **Planner** | Task due dates are the **strings** `"Today"`, `"Tomorrow"` and `"This Week"`, not dates, so a task created a week ago still shows as "Today". The roadmap fallback also marks the first 2 days as `done` automatically. | `system_ai/services.py:13-43`, `features/tasks/TaskList.jsx:21` |
| 12 | **State** | Everything (tasks, roadmap, notifications, gaps, chat history) lives in **one JSON row** per user. The frontend POSTs the *entire* blob 500 ms after every change, which overwrites anything the backend wrote in the meantime (resume or interview gap syncs). | `deployment/schema.sql:23-34`, `hooks/useStatePersistence.js` |
| 13 | **Security** | No token means you are treated as `demo-user-001`, so every endpoint is effectively public. The admin check accepts the literal header `X-Admin-Token: bypassed`, the default password is `"admin"`, and `/admin/auth/verify` **returns the admin password** to anyone who calls it. | `app/core/security.py:15-16, 52-58`, `admin_ai/routes.py:17-21` |
| 14 | **Security / cost** | `/api/mentor/chat` on the backend has **no auth** and accepts an arbitrary `system_prompt` up to 120 KB, which makes it a free, open proxy to your Gemini key. | `backend/modules/mentor_ai/routes.py:28-32` |
| 15 | **Data** | `profiles` rows are never created: there's no DB trigger and `ensure_profile()` is never called. Role lookups always fall back to `student`. | `system_ai/sync.py:13`, `lib/supabase.js:48-54` |

---

## 4. Area-by-area review

### 4.1 Auth and security
- **Demo fallback everywhere.** `get_current_user` returns a shared demo user when there's no token (`security.py:15`). The login page invents a fake user if sign-in fails or returns nothing (`auth/login/page.jsx:29`), and "Demo login" always succeeds (`:41-55`).
- **No route protection.** There's no `middleware.js`, and `/dashboard/*` renders for anyone.
- **Ownership checks are inconsistent.**
  - `resume_ai/services.py:42` (`_get_file_row`) lets anyone analyze anyone's `file_id`.
  - `get_result` allows access whenever `user_id` is null (`:180`). The demo path deliberately sets it to null (`:23-25`).
  - The resume-history fallback query **drops the user filter** and returns every user's rows (`:235-242`). The same pattern exists in `app/shared/db_helpers.py:37-39`.
- **Service-role key used for everything, and no RLS.** The backend bypasses Row Level Security for every query, and no RLS policies exist anyway.
- **JWT.** `import jwt` is used, but `PyJWT` isn't in `requirements.txt`. The code only verifies HS256 with a shared secret. Newer Supabase projects can use asymmetric signing keys, so check which one yours uses.
- **CORS is hardcoded** in `main.py:16-26`, and `settings.ALLOWED_ORIGINS` is ignored.
- **Tokens in localStorage.** The login page writes `auth_token` to localStorage (`login/page.jsx:30`). Supabase already manages the session, so this is redundant.

### 4.2 Data model (`deployment/schema.sql`)
- **`user_system_state` is a god blob.** Tasks, roadmap, notifications, skill gaps, chat context, chat history and chat sessions are all JSONB in one row. You can't query it, you can't index it, and every write is a read-modify-write race (see `sync.py`, `workshops.py`, `admin_ai/services.py:150-178`).
- **IDs are inconsistent.** `user_id` is `TEXT` with no foreign key to `auth.users` on every table except `profiles`. Primary keys are a mix of TEXT, UUID and BIGINT.
- **Schema drift.** Columns the code writes are missing: `weaknesses`, `recommended_roles`, per-answer `strengths`/`gaps`. Columns that exist are never written: `summary`, `overall_feedback`, `profiles.resume_score`, which is why the admin "avg readiness" is always 0.
- **Merge bug.** Skill gaps only ever grow. `merged_gaps[:12]` keeps the *oldest* 12, so once the list is full, new gaps are silently dropped (`sync.py:48,65`).
- **Tables you need but don't have:** goals, plans, dated tasks, job descriptions, interview turns, chat threads and messages.

### 4.3 Resume screening (`backend/modules/resume_ai`)
- **Sections are broken** (see §3 #4). Everything downstream (section reviews, "BS factor", rewrites) is built on that.
- **Fake rewrites.** When the LLM fails, `evaluator.py:99-185` returns **hardcoded "improved" text** (e.g. *"Reduced API response latency by optimizing query paths…"*). The user sees it presented as a rewrite of *their* resume.
- **Up to 7 sequential LLM calls** per analysis (cleanup, semantic, then 5 sections), each with a new HTTP client (`llm_provider.py:24-30`), inside a sync request. It's slow and costly, and each call has its own failure mode.
- **Side effects on reads.** `GET /resume/result` can **re-run the full analysis** (all 7 calls) on read, using `skill_gap` as the target skills (`services.py:186-195`).
- **Score inflation.** `PATCH /resume/result` adds **+5 to the score** whenever "strengths" are added (`services.py:291-293`). It's a vanity bump.
- **Skill detection is a 26-word list** (`constants.py`), so anything outside it is invisible to the deterministic path.
- **Upload validation is inconsistent.** `.doc` is accepted but can't be parsed. `.txt` is offered in the UI but rejected by the backend (`routes.py:28` vs `ResumeUpload.jsx:32`).
- **Scores are blended magic numbers.** `max(35, min(95, …))`, a 60/40 mix, `issue_penalty*2`, `bs_penalty*4`. Nobody can explain them in an interview.
- `ai_provider` is recorded from an unrelated env var and is always "openai" (`services.py:135,152`).

### 4.4 Mock interviews (`backend/modules/interview_ai` + `dashboard/interview`)
- **Questions are one-shot.** They're generated once from a role and a hardcoded level (`'mid-level'`, `interview/page.jsx:103`). There are no follow-ups, no use of the resume or JD, and nothing adaptive, despite what the README claims.
- **Zero scores on bad JSON** (§3 #8) and **misaligned voice answers** (§3 #9).
- **Padding bug.** If the LLM returns too few questions, the code appends the *entire* fallback set, which can exceed `question_count` or duplicate questions (`services.py:166-167`).
- **Fake scorecard.** `generate_feedback_from_transcript` scores by **word count** and always returns the gaps "Technical Depth" and "Structure", then pushes those into the user's profile (`services.py:294-341`).
- **Side effects on reads.** `GET /interview/result` writes to user state (`routes.py:80-92`).
- **Fake history.** The "Recent Sessions" on the interview page are **hardcoded fake cards** with scores of 85 and 92 (`interview/page.jsx:323-339`).
- **N+1 queries.** Interview history makes one query per session (`services.py:346-348`).
- **Dead code.** The Vapi webhook route and both Vapi SDKs are unused. The Vapi webhook is also unauthenticated.

### 4.5 Task planner
- **There is no AI.** Three separate template generators produce near-identical "Practice X for 60 minutes" tasks:
  - `system_ai/services.py:13-43`
  - `api/system/insights/route.js:24-57`
  - `hooks/useDashboardActions.js:66-118`
- **Goals don't drive anything.** `targetRole` and `targetPlacementDate` are stored inside `chatContext`, and nothing reads them to plan.
- **No real dates** (§3 #11). The weekly roadmap falls back to hardcoded **April dates** (`features/tasks/WeeklyRoadmap.jsx:8-34`).
- **Tasks can't be undone.** A completed task can't be un-completed (`AppContext.jsx:67-73`). You also can't add, edit, delete or reschedule tasks.

### 4.6 Dashboard and progress
- **Four different readiness formulas** feed different screens:
  - `intelligence.py:14-74`
  - `AppContext.jsx:128-131`
  - `useDashboard.js:102`
  - `progress/page.jsx:52`
- **Fake numbers.**
  - When loading fails, **mock data is shown to real users**: 72% readiness, 81 interview score, 6 fake tasks (`AppContext.jsx:204`, `lib/mockData.js`).
  - The Progress page **invents a 5-week trend** by subtracting constants from the current score, and computes the "streak" as the number of resumes plus interviews (`progress/page.jsx:66-86`).
  - "Tech Bio Booster" **fabricates resume bullets** ("Architected X, achieving over N stars…") from GitHub star counts (`intelligence.py:76-105`).
- **Wrong axis.** `/system/insights` computes the radar without the GitHub username, so the "Technical" axis is always 0 there (`system_ai/routes.py:111-119`).
- **Every `StatCard` shows `trend="up"`**, whatever the data.

### 4.7 AI chat
- **Broken end-to-end** (§3 #1-3).
- **Two system prompts, neither used correctly.** The client builds one (persona "Antigravity", `ChatInterface.jsx:45-66`) that is ignored. The Next route builds another from data it fails to fetch.
- **Three different LLM paths** for one feature: the Vercel AI SDK in Next, the FastAPI Gemini path, and a template fallback that impersonates AI and tells the user to "add GEMINI_API_KEY on Render".
- **Chat history is stored in the god blob** and re-POSTed in full on every message.
- **No tools.** The chat can't create tasks, start interviews or look anything up. It isn't "agentic".

### 4.8 Frontend architecture
- **Double API layer.** There are 22 Next.js API routes that mostly just proxy to FastAPI, while `next.config.js:12-19` *also* rewrites `/api/*` to the backend. Two of the routes contain business logic that duplicates the backend (`system/insights`, `interview/feedback`).
- **One global context** (`AppContext`) holds everything, with a 500 ms auto-save of the whole state. There's no data-fetching library, so no caching, retries or invalidation.
- **Unused dependencies:**
  - `@vapi-ai/web`, `@vapi-ai/server-sdk`
  - `groq-sdk`, `axios`, `cloudinary`
  - all 7 `@radix-ui/*` packages
  - `pdf-parse` and `mammoth` (only used by the unused `parseFile()`)
  - `ai` and `@ai-sdk/google` (only used by the broken chat route)
- **Unused files:** `components/shared/LoadingSpinner.jsx`, `features/interview/QuestionCard.jsx`, `lib/mockData.js`, `lib/parseFile.js` (only `extractNameFromFilename` is used).
- **No TypeScript and no shared types**, so shape mismatches between backend and frontend (like §3 #3 and #7) are invisible.

### 4.9 Backend architecture
- **Four ways to call an LLM:**
  - Groq through the OpenAI SDK (resume)
  - Gemini through `google-generativeai` (interview, mentor, GitHub)
  - OpenAI direct (interview fallback)
  - the Vercel AI SDK on the frontend

  `google-generativeai` is the legacy Gemini SDK (superseded by `google-genai`), and the default model names (`gemini-1.5-flash`, `gemini-2.0-flash`, `llama-3-8b-8192`) need re-checking against current provider catalogs. There's no timeout, retry, structured-output validation or token/cost logging anywhere.
- **Errors swallowed.** Bare `except Exception` with `print()` is everywhere, so failures are invisible.
- **Circular imports.** Cross-module imports are hidden inside functions to dodge circular dependencies (`admin_ai/services.py:58-62`, the `sync.py` callers).
- **Blocking calls.** Sync LLM and HTTP calls run in request handlers. `build_profile` can make hundreds of sequential GitHub API calls.
- **Global in-memory caches** (`github_profile/services.py:22`) reset on every deploy and aren't shared across workers.
- **Dependencies are unpinned.** `requirements.txt` has no versions, and `pytest` and `PyJWT` are missing.

### 4.10 Tooling, tests, repo
- **Git.** The repo root is `agentic-ai-career-coach/` (remote `Jadui-placement` on GitHub; it's linked from your CV, so treat it as public and never commit personal resumes or `.env` files). **Commit and tag the current state before we delete anything.**
- **Dependencies not installed.** `backend/.venv` contains only pip and setuptools, so the tests can't run as-is. No `node_modules` either.
- **Weak tests.** 3 test files. One tests the admin feature we're deleting. One "passes" while the real parser is broken (§3 #4).
- **No CI, no Dockerfile, no migrations tool.** `schema.sql` is a hand-run script with ad-hoc `ALTER`s at the bottom.
- **README overclaims.** It says "Status: Live", "adaptive question generation", "Vapi voice", "Cloudinary storage", "AI-generated task planning". None of these are true today. **Fix this before it goes on the CV.**

---

## 5. Keep / Rewrite / Delete

### Delete (no longer in scope, or dead)

**Backend**
- `backend/modules/admin_ai/` (whole folder)
- `backend/modules/github_review/` (whole folder)
- `backend/modules/github_profile/` (park it outside the repo if you want it later)
- `backend/modules/system_ai/intelligence.py`, `sync.py` (replaced by the new dashboard and profile services)
- `backend/modules/interview_ai/README.md` (outdated)
- `backend/tests/test_admin_services.py`
- `backend/.pytest_cache/`, `backend/.venv/` (recreate cleanly)

**Frontend**
- `frontend/src/app/admin/` (whole folder) and `frontend/src/features/admin/`
- `frontend/src/app/api/` (**all 22 routes**; the frontend will call FastAPI directly)
- `frontend/src/app/dashboard/github-profile/`, `frontend/src/features/github/`
- `frontend/src/components/dashboard/TechBioBooster.jsx`
- `frontend/src/lib/mockData.js`, `frontend/src/lib/parseFile.js`
- `frontend/src/components/shared/LoadingSpinner.jsx`, `frontend/src/features/interview/QuestionCard.jsx`, `frontend/src/features/interview/InterviewCard.jsx` (only used for the fake history)
- `frontend/src/hooks/useStatePersistence.js`
- From `package.json`: both Vapi SDKs, `groq-sdk`, `axios`, `cloudinary`, all `@radix-ui/*`, `pdf-parse`, `mammoth`, `ai`, `@ai-sdk/google`

**Docs and scratch**
- `docs/module-mapping.md`, `docs/import-process.md`, `docs/hirelens-resume-extraction.md`, `docs/pulseai-interview-extraction.md`, `docs/plans/2026-11-01-production-readiness-remediation.md`
- Parent folder: `a.txt`, `report.txt`, `cleanup_manifesto.md`, `code_audit_report.md`

### Rewrite (keep the idea, replace the implementation)
- `app/core/security.py`: real JWT verification only, no demo fallback, no admin.
- `deployment/schema.sql`: move to versioned migrations (Supabase CLI) with the new tables in §6.
- `resume_ai/`: keep `parser.py` (but preserve line breaks) and the prompt *ideas*. Replace `analyzer`, `evaluator` and `llm_provider` with one structured-output pipeline that supports general and JD modes.
- `interview_ai/`: keep the prompts as a starting point. Rebuild as a turn-based session engine.
- `system_ai/services.py`: replace with separate `planner` and `dashboard` services on real tables.
- `mentor_ai/`: rebuild as `coach`, with a server-side context builder and tool calling.
- `context/AppContext.jsx`: shrink to auth/session only. Move data fetching to per-feature hooks (React Query or SWR).
- Dashboard, tasks, progress and chat pages: rewire to the new endpoints and delete all fake or derived numbers.

### Keep (mostly as-is)
- The stack: Next.js 14 App Router, Tailwind, FastAPI, Supabase.
- Landing page components, `Sidebar` and `TopBar` (update the nav items), `components/ui`, `globals.css`, `tailwind.config.js`.
- `app/shared/json_parser.py`, folded into the new LLM client.
- `resume_ai/parser.py` (with the newline fix) and `tests/test_resume_parser.py`.

---

## 6. Target architecture

### 6.1 Request flow
```
Browser (Next.js) ──Supabase Auth session──▶ FastAPI  (Bearer JWT on every call)
                                               │
                                               ├─ auth: verify JWT → user_id  (no fallback)
                                               ├─ services: resume · interview · planner · dashboard · coach
                                               ├─ llm/: ONE client (provider, timeout, retry, JSON-schema validation, usage log)
                                               └─ db/: repositories per table (Supabase, user-scoped)
                                               ▼
                                          Supabase Postgres (RLS on, FK to auth.users)
```
- **No Next.js API routes.** The frontend calls FastAPI directly at `NEXT_PUBLIC_API_URL`, with the Supabase access token attached.
- **All AI runs in the backend.** No LLM keys on the frontend.
- **Long LLM jobs** (resume analysis, plan generation) return quickly and are polled. Alternatively, run them with an async LLM client and a sensible timeout.

### 6.2 Data model (replaces `user_system_state`)
| Table | Purpose / key columns |
|-------|----------------------|
| `profiles` | `id → auth.users`, name, current level, created by **DB trigger on signup** |
| `goals` | user_id, target_role, target_date, hours_per_week, status |
| `resumes` | user_id, filename, storage_path, **raw_text (line breaks kept)**, created_at |
| `job_descriptions` | user_id, title, company, raw_text, extracted_skills |
| `resume_analyses` | user_id, resume_id, **mode (`general`\|`jd`)**, jd_id?, overall_score, sub_scores JSONB, matched/missing skills, suggestions JSONB, model, prompt_version |
| `interview_sessions` | user_id, source (`role`\|`jd`\|`resume`), role, level, jd_id?, resume_id?, status, final_score, report JSONB |
| `interview_turns` | session_id, idx, question, answer, is_follow_up, scores JSONB, strengths[], gaps[] |
| `plans` | user_id, goal_id, generated_at, summary, version |
| `tasks` | user_id, plan_id?, title, **due_date DATE**, status (`todo`\|`done`\|`skipped`), source (`ai`\|`user`\|`coach`), linked_skill |
| `skill_gaps` | user_id, skill, severity, source (`resume`\|`jd`\|`interview`), source_id, resolved_at |
| `chat_threads` / `chat_messages` | normal relational chat storage |

RLS policies are `user_id = auth.uid()` on every table. Indexes go on `(user_id, created_at)`.

### 6.3 How the pillars connect (the "agentic" story)
1. Resume and JD analyses write rows to `skill_gaps`.
2. Interviews write gaps from each turn's evaluation.
3. The planner reads goal + open gaps + hours/week and writes dated `tasks`.
4. The dashboard reads tasks, analyses, sessions and gaps, then computes **one** documented readiness score.
5. The coach chat calls `build_user_context(user_id)` on the server, which pulls items 1-4, and has tools such as `create_task`, `reschedule_task`, `mark_task_done`, `start_interview(jd_id)` and `get_latest_analysis`.

---

## 7. Fix order (phases)

**Phase 0 — Safety net (½ day)**
- Commit the current state and tag it `pre-rebuild`.
- Delete everything in §5 "Delete". Make sure the app still boots: backend `uvicorn`, frontend `next build`.
- Pin dependencies. Add `PyJWT` and `pytest`. Recreate the venv and run the tests.

**Phase 1 — Foundation (1-2 days)**
- Auth: real JWT verification, no demo user, `middleware.js` to guard `/dashboard`, a profile trigger.
- New schema as migrations, with RLS.
- One `llm` client module: provider config, timeouts, retries, Pydantic-validated JSON output, usage logging.
- A frontend API client that attaches the token, plus React Query. Remove `AppContext` persistence.

**Phase 2 — Resume screening (2 days)**
- Fix the parser (keep line breaks). Single structured LLM call for general review; second mode for JD matching.
- UI: upload or choose a saved resume, choose "General" or "Match to JD" (paste JD), show the results, save to history.
- Tests: parser and section detection on *real* PDF fixtures, plus schema validation of the LLM output.

**Phase 3 — Interviews (2-3 days)**
- Session engine: start (from role, JD or resume), then next question (with follow-up logic), answer, evaluate, finish, report.
- Text mode first. Browser voice only as an input method on top of the same turn API, one answer per turn.
- Save every turn. Write gaps to `skill_gaps`.

**Phase 4 — Goal + planner (2 days)**
- Goal form, then AI plan generation (structured JSON, validated, with real dates), then the task list (CRUD, check/uncheck, reschedule).
- A "Replan" action that uses completed and skipped tasks and new gaps.

**Phase 5 — Dashboard (1 day)**
- One `/dashboard/summary` endpoint. One readiness formula, written down. Real history charts from timestamps. No mock data anywhere.

**Phase 6 — Coach chat (2 days)**
- Server-side context builder and tool calling. Threads and messages in tables. Streaming responses.

**Phase 7 — Polish for CV (1 day)**
- Honest README with architecture diagram, screenshots and the readiness formula.
- CI (lint + tests), a Dockerfile for the backend, `.env.example` files that match the code.

---

## 8. What you can honestly claim on the CV after the rebuild

- "Built a full-stack AI career coach (Next.js, FastAPI, Supabase/Postgres with RLS) with resume–JD matching, adaptive mock interviews, an AI goal planner, and a context-grounded coaching agent with tool calling."
- Be ready to explain: the readiness formula, how LLM output is validated, how the chat context is built, and how a skill gap flows from a resume or interview into a planned task. Those are the interview questions this project will get.

Until then, the current README claims (Live, adaptive interviews, Vapi voice, AI task planning) **don't match the code**. An interviewer who opens the repo will notice.
