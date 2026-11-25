'use client'

import { useState } from 'react'
import { Lightbulb } from 'lucide-react'

import { Badge, Button, Card, CardHeader, Field, Notice, Progress, Segmented, Spinner, Textarea } from '@/components/ui'
import type { PlanDetail } from '@/lib/api/types'
import { cn, formatDay, formatMinutes, formatWeekday, isoDate } from '@/lib/utils'
import { useCheckin, usePlanTasks } from '../hooks'
import { PHASE_HINT, subjectLabel } from '../labels'
import { TaskRow } from './TaskRow'

function addDays(iso: string, days: number) {
  const d = new Date(`${iso}T00:00:00`)
  d.setDate(d.getDate() + days)
  return isoDate(d)
}

/** The next seven days, one block per day. */
export function WeekView() {
  const today = isoDate()
  const end = addDays(today, 6)
  const tasks = usePlanTasks(today, end)
  if (tasks.isLoading) return <Spinner label="Loading tasks…" />
  if (tasks.error) return <Notice>{tasks.error.message}</Notice>
  const days = Array.from({ length: 7 }, (_, i) => addDays(today, i))
  return (
    <div className="space-y-4">
      {days.map((day) => {
        const items = (tasks.data ?? []).filter((t) => t.date === day)
        const minutes = items.reduce((s, t) => s + t.minutes, 0)
        const done = items.filter((t) => t.status === 'done').reduce((s, t) => s + t.minutes, 0)
        return (
          <Card key={day} data-testid={day === today ? 'today-block' : undefined}>
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <h3 className="text-sm">
                {day === today ? 'Today' : day === addDays(today, 1) ? 'Tomorrow' : formatWeekday(day)}
                {day === today && <span className="ml-2 font-normal text-fg-subtle">{formatWeekday(day)}</span>}
              </h3>
              <span className="tabular text-xs text-fg-subtle">{items.length ? `${formatMinutes(done)} / ${formatMinutes(minutes)}` : 'Rest day'}</span>
            </div>
            {items.length > 0 && <ul className="divide-y divide-border px-5">{items.map((t) => <TaskRow key={t.id} task={t} />)}</ul>}
          </Card>
        )
      })}
    </div>
  )
}

/** Phases, weekly milestones, what didn't fit, the AI explanation and project ideas. */
export function RoadmapView({ plan }: { plan: PlanDetail }) {
  const today = isoDate()
  return (
    <div className="space-y-6">
      {plan.summary && (
        <Card className="p-5">
          <div className="flex items-center gap-2">
            <h3 className="text-md">Your plan in short</h3>
            {plan.summary.source === 'ai' && <Badge>AI-written</Badge>}
          </div>
          <p className="mt-2 text-fg-muted">{plan.summary.overview}</p>
        </Card>
      )}

      {!plan.feasibility.fits && (() => { const cut = plan.feasibility.cut ?? []; return (
        <Notice tone="warning">
          <p className="font-medium">Not everything fits in your time.</p>
          {cut.length > 0 && <p className="mt-1">Left out for now: {cut.slice(0, 8).join(', ')}{cut.length > 8 ? '…' : ''}.</p>}
          {plan.feasibility.suggestion && <p className="mt-1">{plan.feasibility.suggestion}</p>}
        </Notice>
      ) })()}

      <Card>
        <CardHeader title="Phases" description={`${formatDay(plan.start_date)} – ${formatDay(plan.target_date)}`} />
        <ol className="divide-y divide-border">
          {plan.roadmap.phases.map((phase) => {
            const now = phase.start <= today && today <= phase.end
            const text = plan.summary?.phases?.find((p) => p.name === phase.name)?.text || PHASE_HINT[phase.name]
            return (
              <li key={phase.name} className="flex gap-4 px-5 py-3.5">
                <span className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', now ? 'bg-primary' : phase.end < today ? 'bg-fg-subtle' : 'border border-border-strong')} aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{phase.name} {now && <Badge tone="primary" className="ml-1">Now</Badge>}</p>
                  <p className="text-xs text-fg-subtle">{formatDay(phase.start)} – {formatDay(phase.end)}</p>
                  {text && <p className="mt-1 text-sm text-fg-muted">{text}</p>}
                </div>
              </li>
            )
          })}
        </ol>
      </Card>

      <Card>
        <CardHeader title="Week by week" description="What you'll finish each week, if you keep to the plan." />
        <ol className="divide-y divide-border">
          {plan.roadmap.weeks.filter((w) => w.minutes > 0).map((week) => {
            const current = week.week_start <= today && today <= addDays(week.week_start, 6)
            const top = Object.entries(week.subjects).sort((a, b) => b[1] - a[1]).slice(0, 3)
            return (
              <li key={week.week_start} className={cn('grid gap-2 px-5 py-3 sm:grid-cols-[120px_1fr]', current && 'bg-primary-soft/50')}>
                <div>
                  <p className="text-sm font-medium">Week of {formatDay(week.week_start)}</p>
                  <p className="text-xs text-fg-subtle">{week.phase} · {formatMinutes(week.minutes)}</p>
                </div>
                <div className="min-w-0 text-sm">
                  <p className="text-fg-muted">{top.map(([s, m]) => `${subjectLabel(s)} ${formatMinutes(m)}`).join(' · ')}</p>
                  {week.finishes.length > 0
                    ? <p className="mt-0.5"><span className="text-fg-subtle">Finish: </span>{week.finishes.join(', ')}</p>
                    : <p className="mt-0.5 text-fg-subtle">Revision, timed practice and mock interviews</p>}
                </div>
              </li>
            )
          })}
        </ol>
      </Card>

      {!!plan.projects?.length && (
        <Card>
          <CardHeader title="Project ideas" description="Suggested for your role and gaps. Pick one for your project tasks." />
          <ul className="grid gap-4 p-5 sm:grid-cols-2">
            {plan.projects.map((p) => (
              <li key={p.title} className="rounded-md border border-border p-4">
                <p className="flex items-center gap-2 font-medium"><Lightbulb className="h-4 w-4 text-warning" aria-hidden /> {p.title}</p>
                <p className="mt-1 text-sm text-fg-muted">{p.why}</p>
                <div className="mt-2 flex flex-wrap gap-1">{p.tech.map((t) => <Badge key={t}>{t}</Badge>)}</div>
                <ol className="mt-3 list-decimal space-y-0.5 pl-5 text-sm text-fg-muted">{p.milestones.map((m) => <li key={m}>{m}</li>)}</ol>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

/** Planned vs done per subject, and every topic's status. */
export function ProgressView({ plan }: { plan: PlanDetail }) {
  const planned = plan.allocation.reduce((s, a) => s + a.planned_minutes, 0)
  const done = plan.allocation.reduce((s, a) => s + a.done_minutes, 0)
  const topicsDone = plan.topics.filter((t) => t.status === 'done').length
  const active = plan.topics.filter((t) => t.status !== 'cut')
  const STATUS = { done: ['success', 'Done'], in_progress: ['primary', 'In progress'], planned: ['neutral', 'Planned'], cut: ['neutral', 'Left out'] } as const
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-5"><p className="text-sm text-fg-muted">Study time done</p><p className="tabular mt-1 text-2xl font-semibold">{formatMinutes(done)}</p><p className="text-xs text-fg-subtle">of {formatMinutes(planned)} planned</p></Card>
        <Card className="p-5"><p className="text-sm text-fg-muted">Topics finished</p><p className="tabular mt-1 text-2xl font-semibold">{topicsDone}</p><p className="text-xs text-fg-subtle">of {active.length} in the plan</p></Card>
        <Card className="p-5"><p className="text-sm text-fg-muted">Plan capacity</p><p className="tabular mt-1 text-2xl font-semibold">{Math.round(plan.capacity_factor * 100)}%</p><p className="text-xs text-fg-subtle">of your stated hours (updated by check-ins)</p></Card>
      </div>
      <Card>
        <CardHeader title="By subject" description="Bar = done; the share is how much of your time each subject gets." />
        <ul className="space-y-4 p-5">
          {plan.allocation.filter((a) => a.planned_minutes > 0).map((a) => (
            <li key={a.subject}>
              <div className="flex justify-between text-sm">
                <span>{subjectLabel(a.subject)} <span className="text-xs text-fg-subtle">· {a.weight}% of time</span></span>
                <span className="tabular text-fg-muted">{formatMinutes(a.done_minutes)} / {formatMinutes(a.planned_minutes)}</span>
              </div>
              <Progress value={a.done_minutes} max={a.planned_minutes} className="mt-1.5" label={subjectLabel(a.subject)} />
            </li>
          ))}
        </ul>
      </Card>
      <Card>
        <CardHeader title="Topics" />
        <ul className="divide-y divide-border">
          {plan.topics.map((t) => {
            const [tone, label] = STATUS[t.status as keyof typeof STATUS] ?? STATUS.planned
            return (
              <li key={t.topic_id} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                <span className="w-24 shrink-0 text-xs text-fg-subtle">{subjectLabel(t.subject)}</span>
                <span className={cn('min-w-0 flex-1', t.status === 'cut' && 'text-fg-subtle line-through')}>{t.title}</span>
                {t.source !== 'curriculum' && t.source !== 'checkpoint' && <Badge tone="warning">From your gaps</Badge>}
                <Badge tone={tone}>{label}</Badge>
              </li>
            )
          })}
        </ul>
      </Card>
    </div>
  )
}

/** Weekly check-in: three quick answers; the plan adapts to what you really did. */
export function CheckinCard() {
  const checkin = useCheckin()
  const [difficulty, setDifficulty] = useState<'too_easy' | 'right' | 'too_hard'>('right')
  const [note, setNote] = useState('')
  const [busyStart, setBusyStart] = useState('')
  const [busyEnd, setBusyEnd] = useState('')
  const [hidden, setHidden] = useState(false)
  if (hidden) return null
  const submit = () => checkin.mutate({
    difficulty, note: note.trim() || null,
    busy: busyStart && busyEnd ? [{ start: busyStart, end: busyEnd, label: 'From check-in' }] : [],
  }, { onSuccess: () => setHidden(true) })
  return (
    <Card className="border-primary/40" data-testid="checkin">
      <CardHeader title="Weekly check-in" description="How did last week go? Your answers adjust the plan; nothing else changes." />
      <div className="space-y-4 p-5">
        <Field label="The work felt…">
          <Segmented value={difficulty} onChange={setDifficulty} label="Difficulty" options={[
            { value: 'too_easy', label: 'Too easy' }, { value: 'right', label: 'About right' }, { value: 'too_hard', label: 'Too hard' }]} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Busy coming up? From" htmlFor="busy-start"><input id="busy-start" type="date" className="input-base" value={busyStart} onChange={(e) => setBusyStart(e.target.value)} /></Field>
          <Field label="to" htmlFor="busy-end"><input id="busy-end" type="date" className="input-base" value={busyEnd} onChange={(e) => setBusyEnd(e.target.value)} /></Field>
        </div>
        <Field label="Anything else (optional)" htmlFor="checkin-note">
          <Textarea id="checkin-note" rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        {checkin.error && <Notice>{checkin.error.message}</Notice>}
        <div className="flex gap-2">
          <Button onClick={submit} loading={checkin.isPending}>Save check-in</Button>
          <Button variant="ghost" onClick={() => setHidden(true)}>Later</Button>
        </div>
      </div>
    </Card>
  )
}
