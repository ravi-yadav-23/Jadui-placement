# Backlog

Deferred tasks to do before the project is called finished. Tick them off as you go.

## Resume screener: go-live (from the v2 build, 2026-11-25)

- [ ] **Fix the model name in `backend/.env`.** `gemini-2.0-flash` was shut down on 2026-06-01, so every
      Gemini call in the current app fails. Set `LLM_PRIMARY_MODEL=gemini-3.8-flash` (and `GEMINI_MODEL` for
      the legacy modules). Check current IDs: https://ai.google.dev/gemini-api/docs/deprecations
- [ ] **Apply the database migration** `supabase/migrations/20261124000000_resume_v2.sql`
      (Supabase SQL editor, or `supabase db push`).
- [ ] **Run the real eval** from `backend/`: `python -m evals.resume.run --out ../docs/evals/resume-v1.md`.
      It sends only the made-up resumes in `evals/resume/cases.yaml` and costs a few cents. This is also the
      first real check that Gemini accepts the output schemas. Tune prompts from the results.
- [ ] **First real end-to-end run** against Supabase (not memory/fake mode): upload, review, JD match.
      Not yet verified: the Supabase data layer and JWKS (asymmetric key) login.
- [ ] **Check the GitHub Actions run on `main`** (backend, frontend, e2e) at
      https://github.com/ravi-yadav-23/Jadui-placement/actions
- [ ] **Update CV bullets** in `CV Optimizer/profile/projects/jadui-placement.json`: mark the old,
      inaccurate Jadui bullets unverified; add the new ones (draft in `docs/learn/resume-screener-guide.md`
      §12) with numbers from the eval report.

## Cleanup leftovers (from the Phase 0 cleanup, 2026-11-25)

- [ ] **Drop the unused tables in Supabase** once you have checked they hold nothing you want to keep:
      `workshops`, `github_pr_reviews`, `github_repo_analyses`, and the `role` column on `profiles`
      (the code that used them is deleted). Not done automatically because dropping tables deletes data.
- [ ] **Delete the old audit files in the parent folder** (`../a.txt`, `../report.txt`,
      `../cleanup_manifesto.md`, `../code_audit_report.md`). They are outside git, so deleting them cannot be
      undone; `REVIEW.md` replaces them.
- [ ] **Pick a license.** The README used to say MIT and link a `LICENSE` file that does not exist. Add one
      (e.g. MIT) if you want others to reuse the code.

## Mock interviews: go-live (from the v2 build, 2026-11-25)

- [ ] **Review the question bank** (`backend/app/interview/data/fundamentals.yaml`, `behavioral.yaml`): fix any
      key point you disagree with. Wrong key points teach wrong answers.
- [ ] **Apply the migration** `supabase/migrations/20261126000000_interview_v2.sql` (after the resume one).
- [ ] **Run the real eval** from `backend/`: `python -m evals.interview.run --out ../docs/evals/interview-v1.md`.
      Check key-point precision, the padding and injection rows, and HR answers; tune `interview_judge` if needed.
- [ ] **Try a real interview** in Chrome with voice, then one in practice mode.
- [ ] **Drop the legacy interview tables** `interview_sessions` and `interview_answers` once you've checked
      nothing in them is worth keeping (the code that used them is deleted).
- [ ] **Update CV bullets** with numbers from the eval report (drafts in `docs/learn/mock-interview-guide.md` §14).

## Planner, coach and v1 app: go-live (2026-11-26)

- [ ] **Apply the new migrations, in order:** `20261127000000_planner_v2.sql`, then `20261128000000_coach.sql`
      (after the resume and interview ones).
- [ ] **Review the curriculum** in `backend/app/planner/curriculum/*.yaml`: topics, minutes, suggested problems,
      resources and the subject weights in `weights.yaml`. Then run `python -m evals.planner.run` from `backend/`.
- [ ] **Supabase Auth settings** (dashboard → Authentication → URL configuration): set the Site URL to your
      deployed frontend and add `/auth/reset` and `/dashboard` as redirect URLs (password reset and email
      confirmation links land there).
- [ ] **Deploy env vars**: frontend needs only `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` and
      `NEXT_PUBLIC_BACKEND_URL` (no AI keys on the frontend any more). Backend: see `.env.example`.
- [ ] **Try the full loop with a real account**: sign up → questionnaire → plan → tick tasks → mock interview →
      coach. Check that the AI roadmap summary and project ideas appear (they fall back to templates silently).
- [ ] **Drop the legacy tables** once you've checked there's nothing to keep. The code that used them is deleted:
      ```sql
      drop table if exists public.user_system_state, public.resume_files, public.resume_results,
        public.interview_sessions, public.interview_answers, public.workshops, public.github_pr_reviews,
        public.github_repo_analyses cascade;
      alter table public.profiles drop column if exists role;   -- only if a legacy profiles table exists
      ```
- [ ] **Update CV bullets** with the planner and coach drafts (`docs/learn/task-planner-guide.md` §12).
