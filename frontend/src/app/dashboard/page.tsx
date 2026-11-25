'use client'

import Link from 'next/link'
import { ArrowRight, Check, CircleDashed, FileText, Flame, Mic, CalendarCheck, Sparkles } from 'lucide-react'

import { Badge, ButtonLink, Card, CardHeader, EmptyState, Progress, Skeleton, Sparkline, Notice } from '@/components/ui'
import { useAuth } from '@/features/auth/AuthProvider'
import { useDashboard } from '@/features/coach/hooks'
import { TaskRow } from '@/features/planner/components/TaskRow'
import type { DashboardOverview } from '@/lib/api/types'
import { cn, formatDay, formatMinutes, scoreTone, timeAgo, TONE_TEXT } from '@/lib/utils'

const ACTIVITY_ICON = { resume: FileText, interview: Mic, plan: CalendarCheck, tasks: Check } as const

function greeting() {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
}

/** Today: what to do now, how ready you are, and what happened recently. */
export default function TodayPage() {
  const { user } = useAuth()
  const dashboard = useDashboard()
  const data = dashboard.data

  return (
    <>
      <header className="mb-6">
        <p className="text-sm text-fg-muted">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
        <h1 className="mt-1 text-2xl">{greeting()}, {user?.name}</h1>
      </header>

      {dashboard.error && <Notice className="mb-6">{dashboard.error.message}</Notice>}
      {!data && !dashboard.error && <LoadingState />}
      {data && (
        <div className="space-y-6">
          {data.setup.some((s) => !s.done) && <SetupChecklist steps={data.setup} />}
          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            <div className="space-y-6">
              <TodayTasks data={data} />
              <NextActions data={data} />
            </div>
            <div className="space-y-6">
              <ReadinessCard data={data} />
              <WeekCard data={data} />
            </div>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <ActivityCard data={data} />
            <GapsCard data={data} />
          </div>
        </div>
      )}
    </>
  )
}

function LoadingState() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <Skeleton className="h-72" />
      <Skeleton className="h-72" />
    </div>
  )
}

function SetupChecklist({ steps }: { steps: DashboardOverview['setup'] }) {
  const done = steps.filter((s) => s.done).length
  return (
    <Card data-testid="setup-checklist">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-4">
        <div>
          <h2 className="text-md">Get set up</h2>
          <p className="text-sm text-fg-muted">Four steps, about 15 minutes. Each one makes the others more useful.</p>
        </div>
        <span className="tabular text-sm text-fg-muted">{done} of {steps.length} done</span>
      </div>
      <Progress value={done} max={steps.length} className="mx-5 mt-3 w-auto" label="Setup progress" />
      <ol className="grid gap-px p-2 sm:grid-cols-4">
        {steps.map((step) => (
          <li key={step.key}>
            <Link href={step.href} className={cn('flex h-full items-center gap-2.5 rounded-md px-3 py-2.5 text-sm transition-colors',
              step.done ? 'text-fg-subtle' : 'font-medium hover:bg-subtle')}>
              {step.done
                ? <Check className="h-4 w-4 shrink-0 text-success" aria-label="Done" />
                : <CircleDashed className="h-4 w-4 shrink-0 text-fg-subtle" aria-hidden />}
              <span className={cn(step.done && 'line-through')}>{step.label}</span>
            </Link>
          </li>
        ))}
      </ol>
    </Card>
  )
}

function TodayTasks({ data }: { data: DashboardOverview }) {
  const today = data.today
  const tasks = today.today ?? []
  const left = tasks.filter((t) => t.status === 'todo')
  const minutesLeft = left.reduce((sum, t) => sum + t.minutes, 0)
  return (
    <Card>
      <CardHeader title="Today's tasks"
        description={today.has_plan ? (left.length ? `${left.length} left · about ${formatMinutes(minutesLeft)}` : 'All done for today') : undefined}
        action={today.has_plan ? <ButtonLink href="/dashboard/planner" variant="ghost" size="sm">Planner <ArrowRight className="h-3.5 w-3.5" /></ButtonLink> : undefined} />
      <div className="px-5 py-2">
        {!today.has_plan && (
          <EmptyState className="my-3" icon={<CalendarCheck className="h-6 w-6" />} title="No study plan yet"
            description="Answer five short questions about your goal and your time; you get a day-by-day plan."
            action={<ButtonLink href="/dashboard/planner/setup">Create my plan</ButtonLink>} />
        )}
        {today.has_plan && tasks.length === 0 && (
          <p className="py-6 text-center text-sm text-fg-muted">Nothing planned today: it&apos;s a rest day or a busy day you marked.</p>
        )}
        {today.has_plan && tasks.length > 0 && (
          <ul className="divide-y divide-border">{tasks.map((t) => <TaskRow key={t.id} task={t} />)}</ul>
        )}
      </div>
    </Card>
  )
}

function ReadinessCard({ data }: { data: DashboardOverview }) {
  const { readiness } = data
  return (
    <Card data-testid="readiness">
      <div className="px-5 pt-4">
        <h2 className="text-md">Readiness</h2>
        {readiness.score === null ? (
          <p className="mt-2 text-sm text-fg-muted">Not enough data yet. It appears once two of the parts below have data.</p>
        ) : (
          <p className="mt-1 flex items-baseline gap-1">
            <span className={cn('tabular text-4xl font-semibold', TONE_TEXT[scoreTone(readiness.score)])}>{readiness.score}</span>
            <span className="text-sm text-fg-subtle">/ 100</span>
          </p>
        )}
      </div>
      <ul className="space-y-3 px-5 py-4">
        {readiness.parts.map((part) => (
          <li key={part.key}>
            <div className="flex items-baseline justify-between text-sm">
              <span>{part.label} <span className="text-xs text-fg-subtle">· {part.weight}%</span></span>
              <span className="tabular font-medium">{part.value ?? '—'}</span>
            </div>
            <Progress value={part.value ?? 0} tone={part.value === null ? 'neutral' : scoreTone(part.value)} className="mt-1.5" label={part.label} />
            <p className="mt-1 text-xs text-fg-subtle">{part.detail}</p>
            {part.key === 'interviews' && data.interview_trend.length > 1 && <Sparkline values={data.interview_trend} className="mt-1" />}
          </li>
        ))}
      </ul>
      <details className="border-t border-border px-5 py-3 text-xs text-fg-muted">
        <summary className="cursor-pointer select-none">How is this calculated?</summary>
        <p className="mt-1.5">{readiness.formula}</p>
      </details>
    </Card>
  )
}

function WeekCard({ data }: { data: DashboardOverview }) {
  const t = data.today
  if (!t.has_plan) return null
  return (
    <Card className="space-y-4 p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-md">This week</h2>
        {t.on_track === false ? <Badge tone="warning">Behind</Badge> : <Badge tone="success">On track</Badge>}
      </div>
      <div>
        <div className="flex justify-between text-sm">
          <span className="text-fg-muted">Study time</span>
          <span className="tabular">{formatMinutes(t.week_done_minutes)} / {formatMinutes(t.week_planned_minutes)}</span>
        </div>
        <Progress value={t.week_done_minutes} max={t.week_planned_minutes || 1} className="mt-1.5" label="Study time this week" />
      </div>
      <div className="flex items-center gap-2 text-sm">
        <Flame className={cn('h-4 w-4', t.streak_days ? 'text-warning' : 'text-fg-subtle')} aria-hidden />
        <span>{t.streak_days ? `${t.streak_days}-day streak` : 'No streak yet: finish a task today'}</span>
      </div>
      {t.next_milestone && <p className="text-sm text-fg-muted"><span className="font-medium text-fg">Next: </span>{t.next_milestone}</p>}
      {t.target_date && <p className="text-xs text-fg-subtle">Target date {formatDay(t.target_date)}</p>}
    </Card>
  )
}

function NextActions({ data }: { data: DashboardOverview }) {
  if (!data.next_actions.length) return null
  return (
    <Card>
      <CardHeader title="Suggested next" />
      <ul className="divide-y divide-border">
        {data.next_actions.map((a) => (
          <li key={a.label}>
            <Link href={a.href} className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-subtle">
              <span>
                <span className="block text-sm font-medium">{a.label}</span>
                <span className="block text-xs text-fg-muted">{a.reason}</span>
              </span>
              <ArrowRight className="h-4 w-4 shrink-0 text-fg-subtle" aria-hidden />
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function ActivityCard({ data }: { data: DashboardOverview }) {
  return (
    <Card>
      <CardHeader title="Recent activity" />
      {data.activity.length === 0 ? (
        <p className="px-5 py-6 text-sm text-fg-muted">Your reviews, interviews and finished tasks will show up here.</p>
      ) : (
        <ul className="px-5 py-2">
          {data.activity.map((item, i) => {
            const Icon = ACTIVITY_ICON[item.kind as keyof typeof ACTIVITY_ICON] ?? Sparkles
            const body = (
              <span className="flex items-center gap-3 py-2">
                <Icon className="h-4 w-4 shrink-0 text-fg-subtle" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-sm">{item.title}</span>
                <span className="shrink-0 text-xs text-fg-subtle">{timeAgo(item.at)}</span>
              </span>
            )
            return <li key={i}>{item.href ? <Link href={item.href} className="block hover:text-primary">{body}</Link> : body}</li>
          })}
        </ul>
      )}
    </Card>
  )
}

function GapsCard({ data }: { data: DashboardOverview }) {
  const source = { jd_match: 'JD match', resume_review: 'Resume', interview: 'Interview' } as Record<string, string>
  return (
    <Card>
      <CardHeader title="Open skill gaps" description="Found by your resume review, JD matches and mock interviews." />
      {data.open_gaps.length === 0 ? (
        <p className="px-5 py-6 text-sm text-fg-muted">No open gaps. Run a JD match or a mock interview to find what to work on.</p>
      ) : (
        <ul className="flex flex-wrap gap-2 px-5 py-4">
          {data.open_gaps.map((g) => (
            <li key={g.skill}><Badge tone="warning" className="px-2 py-1">{g.skill} <span className="font-normal opacity-70">· {source[g.source] ?? g.source}</span></Badge></li>
          ))}
        </ul>
      )}
    </Card>
  )
}
