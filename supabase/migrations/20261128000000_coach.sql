-- Coach chat: one conversation per user. Same rules as the other v2 tables (owner-only RLS).
create table if not exists public.coach_messages (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       text not null check (role in ('user', 'assistant')),
  content    text not null,
  actions    jsonb not null default '[]',   -- proposed buttons (validated); they run only when clicked
  created_at timestamptz not null default now()
);

create index if not exists coach_messages_user_created on public.coach_messages (user_id, created_at desc);

alter table public.coach_messages enable row level security;
drop policy if exists own_coach_messages on public.coach_messages;
create policy own_coach_messages on public.coach_messages
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
