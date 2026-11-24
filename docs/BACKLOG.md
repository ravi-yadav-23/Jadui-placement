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
- [ ] **Push `feat/resume-v2`** and check the GitHub Actions run (backend, frontend, e2e).
- [ ] **Update CV bullets** in `CV Optimizer/profile/projects/jadui-placement.json`: mark the old,
      inaccurate Jadui bullets unverified; add the new ones (draft in `docs/learn/resume-screener-guide.md`
      §12) with numbers from the eval report.
- [ ] **Optional: update the local git remote.** The repo moved to `ravi-yadav-23/Jadui-placement` (the old
      `Ravi-Dahiya-00` URL still redirects): `git remote set-url origin https://github.com/ravi-yadav-23/Jadui-placement.git`
