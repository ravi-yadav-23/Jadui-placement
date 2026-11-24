-- Mock Interviews v2 schema.
-- New table names: the legacy schema already has interview_sessions / interview_answers (left untouched).
-- Same rules as resume v2: user_id -> auth.users ON DELETE CASCADE, RLS owner-only,
-- and the backend (service-role key) always filters by user_id itself.

-- One mock interview session.
create table if not exists public.interviews (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  track           text not null check (track in ('resume', 'jd', 'fundamentals', 'behavioral', 'mixed')),
  mode            text not null default 'interview' check (mode in ('interview', 'practice')),
  resume_id       uuid references public.resumes(id) on delete set null,
  jd_id           uuid references public.job_descriptions(id) on delete set null,
  target_role     text,
  settings        jsonb not null default '{}',   -- question_count, topics, difficulty, seed
  plan            jsonb not null default '[]',   -- planned questions + key points; never sent to the browser early
  status          text not null default 'planning'
                  check (status in ('planning', 'active', 'completed', 'failed')),
  score           int,
  report          jsonb,
  prompt_versions jsonb not null default '{}',
  error           text,
  created_at      timestamptz not null default now(),
  completed_at    timestamptz
);

-- One question asked + the answer given (a main question or its follow-up).
create table if not exists public.interview_turns (
  id               uuid primary key default gen_random_uuid(),
  interview_id     uuid not null references public.interviews(id) on delete cascade,
  user_id          uuid not null references auth.users(id) on delete cascade,
  idx              int  not null,               -- order in the session: 0, 1, 2, ...
  question_id      text not null,               -- plan id: q0, q1, ...
  kind             text not null check (kind in ('main', 'follow_up')),
  question         text not null,
  answer           text,
  answer_mode      text check (answer_mode in ('text', 'voice')),
  duration_seconds int,
  delivery         jsonb,                       -- words per minute, filler words, repeated words
  evaluation       jsonb,                       -- validated TurnEvaluation
  score            int,
  status           text not null default 'asked'
                   check (status in ('asked', 'evaluating', 'evaluated', 'skipped', 'failed')),
  error            text,
  created_at       timestamptz not null default now(),
  answered_at      timestamptz,
  unique (interview_id, idx)
);

create index if not exists interviews_user_created on public.interviews (user_id, created_at desc);
create index if not exists interview_turns_session on public.interview_turns (interview_id, idx);

alter table public.interviews      enable row level security;
alter table public.interview_turns enable row level security;

drop policy if exists own_interviews on public.interviews;
create policy own_interviews on public.interviews
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_interview_turns on public.interview_turns;
create policy own_interview_turns on public.interview_turns
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
