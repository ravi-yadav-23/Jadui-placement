-- Resume Screener v2 schema.
-- Apply with the Supabase CLI (`supabase db push`) or paste into the SQL editor.
-- Every user-owned table: user_id -> auth.users, ON DELETE CASCADE, RLS owner-only.
-- The backend uses the service-role key (bypasses RLS) and ALWAYS filters by user_id itself;
-- RLS is the second line of defence if a client ever talks to these tables directly.

create extension if not exists pgcrypto;

-- One uploaded resume file (a "version"). Same file uploaded twice -> same row (file_sha256).
create table if not exists public.resumes (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references auth.users(id) on delete cascade,
  title          text not null,
  storage_path   text not null,
  file_sha256    text not null,
  mime_type      text not null,
  page_count     int  not null default 0,
  raw_text       text,                          -- reading-order text, newlines preserved
  extract_meta   jsonb not null default '{}',   -- columns, images, odd glyphs, header/footer text
  checks         jsonb not null default '[]',   -- parse-health checks
  contacts       jsonb not null default '{}',   -- regex-extracted email/phone/links
  profile        jsonb,                         -- structured ResumeProfile (LLM, then user-editable)
  profile_edited boolean not null default false,
  status         text not null default 'queued'
                 check (status in ('queued', 'processing', 'ready', 'failed')),
  error          text,
  created_at     timestamptz not null default now(),
  unique (user_id, file_sha256)
);
create index if not exists resumes_user_created_idx on public.resumes (user_id, created_at desc);

-- A pasted job description, parsed once and reused (text_sha256).
create table if not exists public.job_descriptions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  title       text,
  company     text,
  raw_text    text not null,
  text_sha256 text not null,
  parsed      jsonb,                            -- JobRequirements
  status      text not null default 'queued'
              check (status in ('queued', 'processing', 'ready', 'failed')),
  error       text,
  created_at  timestamptz not null default now(),
  unique (user_id, text_sha256)
);
create index if not exists jds_user_created_idx on public.job_descriptions (user_id, created_at desc);

-- One analysis run: general review or JD match.
create table if not exists public.resume_analyses (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  resume_id       uuid not null references public.resumes(id) on delete cascade,
  jd_id           uuid references public.job_descriptions(id) on delete set null,
  mode            text not null check (mode in ('general', 'jd')),
  target_role     text,
  status          text not null default 'queued'
                  check (status in ('queued', 'running', 'done', 'failed')),
  error           text,
  input_hash      text not null,                -- cache key: same inputs -> reuse result
  overall_score   int,
  sub_scores      jsonb,
  result          jsonb,
  prompt_versions jsonb not null default '{}',
  model           text,
  created_at      timestamptz not null default now(),
  completed_at    timestamptz
);
create index if not exists analyses_user_created_idx on public.resume_analyses (user_id, created_at desc);
create index if not exists analyses_input_hash_idx on public.resume_analyses (user_id, input_hash);

-- Skill gaps found by any pillar; the planner and coach chat read these later.
create table if not exists public.skill_gaps (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  skill       text not null,
  severity    text not null check (severity in ('must_have', 'nice_to_have', 'general')),
  source      text not null check (source in ('resume_review', 'jd_match', 'interview')),
  source_id   uuid not null,
  resolved_at timestamptz,
  created_at  timestamptz not null default now(),
  unique (user_id, skill, source, source_id)
);

-- Every LLM call: for cost, latency and debugging. Never stores prompt or resume text.
create table if not exists public.llm_calls (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid references auth.users(id) on delete set null,
  purpose        text not null,
  provider       text not null,
  model          text not null,
  prompt_version text not null,
  input_tokens   int,
  output_tokens  int,
  latency_ms     int,
  ok             boolean not null,
  error          text,
  created_at     timestamptz not null default now()
);

-- Row Level Security: owners only.
alter table public.resumes          enable row level security;
alter table public.job_descriptions enable row level security;
alter table public.resume_analyses  enable row level security;
alter table public.skill_gaps       enable row level security;
alter table public.llm_calls        enable row level security;  -- no policy: backend-only

drop policy if exists own_resumes on public.resumes;
create policy own_resumes on public.resumes
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_jds on public.job_descriptions;
create policy own_jds on public.job_descriptions
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_analyses on public.resume_analyses;
create policy own_analyses on public.resume_analyses
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_gaps on public.skill_gaps;
create policy own_gaps on public.skill_gaps
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Private bucket for original files: resumes/{user_id}/{resume_id}.{pdf|docx}
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;
