-- Task Planner v2 schema. Same rules as resume/interview v2: user_id -> auth.users ON DELETE CASCADE,
-- RLS owner-only, and the backend (service-role key) always filters by user_id itself.

-- The questionnaire answers (one row per user).
create table if not exists public.planner_profiles (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null unique references auth.users(id) on delete cascade,
  answers    jsonb not null,                       -- validated PlannerProfile
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- One roadmap. Creating a new one archives the previous one.
create table if not exists public.plans (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references auth.users(id) on delete cascade,
  status             text not null default 'active' check (status in ('active', 'archived')),
  start_date         date not null,
  target_date        date not null,
  profile_snapshot   jsonb not null,               -- the answers this plan was built from
  settings           jsonb not null default '{}',  -- language, minutes per problem, level
  allocation         jsonb not null,               -- planned minutes per subject + weights
  roadmap            jsonb not null,               -- phases and weekly milestones
  feasibility        jsonb not null,               -- fits?, cut topics, suggestion, on-track status
  capacity_factor    numeric not null default 0.85,
  summary            jsonb,                        -- roadmap explanation (AI or template)
  projects           jsonb,                        -- AI project ideas
  curriculum_version text not null,
  refreshed_on       date,
  created_at         timestamptz not null default now()
);

-- Every topic in the plan with its progress. Rows are self-contained (title, prerequisites, sizes),
-- so re-planning never needs the curriculum files.
create table if not exists public.plan_topics (
  id              uuid primary key default gen_random_uuid(),
  plan_id         uuid not null references public.plans(id) on delete cascade,
  user_id         uuid not null references auth.users(id) on delete cascade,
  topic_id        text not null,
  subject         text not null,
  title           text not null,
  priority        text not null check (priority in ('must', 'should', 'nice')),
  source          text not null default 'curriculum'
                  check (source in ('curriculum', 'resume_gap', 'interview_gap', 'checkpoint')),
  position        int  not null,                   -- order inside the subject
  planned_minutes int  not null,
  learn_minutes   int  not null default 0,         -- DSA: the theory part before practice
  prerequisites   jsonb not null default '[]',
  details         jsonb not null default '{}',     -- resource, suggested problems, interview link
  done_minutes    int  not null default 0,
  status          text not null default 'planned' check (status in ('planned', 'in_progress', 'done', 'cut')),
  learned_on      date,
  review_stage    int  not null default 0,         -- spaced reviews done: 0..3 (+2, +7, +21 days)
  created_at      timestamptz not null default now(),
  unique (plan_id, topic_id)
);

-- Dated tasks for the next 14 days (rebuilt as the plan rolls forward).
create table if not exists public.plan_tasks (
  id         uuid primary key default gen_random_uuid(),
  plan_id    uuid not null references public.plans(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  date       date not null,
  position   int  not null,
  kind       text not null check (kind in ('learn', 'practice', 'review', 'project', 'mock', 'checkpoint')),
  subject    text not null,
  topic_id   text,
  title      text not null,
  minutes    int  not null,
  details    jsonb not null default '{}',           -- problems, resource, interview link, pinned
  status     text not null default 'todo' check (status in ('todo', 'done', 'skipped')),
  done_at    timestamptz,
  created_at timestamptz not null default now()
);

-- Weekly check-ins: real completion rate -> future capacity.
create table if not exists public.plan_checkins (
  id              uuid primary key default gen_random_uuid(),
  plan_id         uuid not null references public.plans(id) on delete cascade,
  user_id         uuid not null references auth.users(id) on delete cascade,
  week_start      date not null,
  planned_minutes int  not null,
  done_minutes    int  not null,
  difficulty      text check (difficulty in ('too_easy', 'right', 'too_hard')),
  note            text,
  created_at      timestamptz not null default now(),
  unique (plan_id, week_start)
);

create index if not exists plans_user_created on public.plans (user_id, created_at desc);
create index if not exists plan_tasks_plan_date on public.plan_tasks (plan_id, date);
create index if not exists plan_topics_plan on public.plan_topics (plan_id);

alter table public.planner_profiles enable row level security;
alter table public.plans            enable row level security;
alter table public.plan_topics      enable row level security;
alter table public.plan_tasks       enable row level security;
alter table public.plan_checkins    enable row level security;

drop policy if exists own_planner_profiles on public.planner_profiles;
create policy own_planner_profiles on public.planner_profiles
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_plans on public.plans;
create policy own_plans on public.plans
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_plan_topics on public.plan_topics;
create policy own_plan_topics on public.plan_topics
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_plan_tasks on public.plan_tasks;
create policy own_plan_tasks on public.plan_tasks
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists own_plan_checkins on public.plan_checkins;
create policy own_plan_checkins on public.plan_checkins
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
