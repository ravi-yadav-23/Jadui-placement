'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { CalendarClock, ChevronDown, ExternalLink, Mic, SkipForward, Undo2 } from 'lucide-react'

import { Badge, Button, Dialog, Field, Input, Notice } from '@/components/ui'
import type { PlanTask } from '@/lib/api/types'
import { cn, formatMinutes, isoDate } from '@/lib/utils'
import { useMoveTask, useUpdateTask } from '../hooks'
import { KINDS, subjectLabel } from '../labels'

type Details = {
  problems?: string[]; resource?: { title: string; url: string }; how?: string; missed?: boolean; pinned?: boolean
  interview?: { track: string; topics?: string[] }
}

export function interviewHref(interview: { track: string; topics?: string[] }) {
  const params = new URLSearchParams({ track: interview.track })
  if (interview.topics?.length) params.set('topics', interview.topics.join(','))
  return `/dashboard/interview?${params}`
}

/** One task: checkbox, title, subject/kind/time, and details (problems, resource, mock interview link). */
export function TaskRow({ task, readOnly = false }: { task: PlanTask; readOnly?: boolean }) {
  const update = useUpdateTask()
  const [open, setOpen] = useState(false)
  const [moving, setMoving] = useState(false)
  // Optimistic status: the checkbox responds instantly; it rolls back if the request fails.
  const [status, setStatus] = useState(task.status)
  useEffect(() => { setStatus(task.status) }, [task.status])
  const setTo = (next: PlanTask['status']) => {
    setStatus(next)
    update.mutate({ id: task.id, status: next }, { onError: () => setStatus(task.status) })
  }
  const details = task.details as Details
  const done = status === 'done'
  const skipped = status === 'skipped'
  const hasDetails = Boolean(details.problems?.length || details.resource || details.how || details.interview)

  return (
    <li className="group" data-testid="task-row">
      <div className="flex items-start gap-3 py-2.5">
        <input type="checkbox" checked={done} disabled={readOnly || skipped}
          onChange={() => setTo(done ? 'todo' : 'done')}
          aria-label={done ? `Mark "${task.title}" as not done` : `Mark "${task.title}" as done`}
          className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer rounded accent-[rgb(var(--primary))]" />
        <div className="min-w-0 flex-1">
          <button type="button" onClick={() => hasDetails && setOpen(!open)} disabled={!hasDetails}
            className={cn('flex w-full items-start gap-1 text-left text-sm', (done || skipped) && 'text-fg-subtle line-through')}>
            <span className="min-w-0 flex-1">{task.title}</span>
            {hasDetails && <ChevronDown className={cn('mt-0.5 h-4 w-4 shrink-0 text-fg-subtle transition-transform', open && 'rotate-180')} aria-hidden />}
          </button>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-fg-subtle">
            <span>{subjectLabel(task.subject)}</span>
            <span aria-hidden>·</span>
            <span>{KINDS[task.kind]}</span>
            <span aria-hidden>·</span>
            <span className="tabular">{formatMinutes(task.minutes)}</span>
            {details.missed && <Badge tone="warning">Missed, re-planned</Badge>}
            {skipped && !details.missed && <Badge>Skipped</Badge>}
            {details.pinned && <Badge>Moved</Badge>}
          </div>
          {open && <TaskDetails details={details} />}
        </div>
        {!readOnly && status === 'todo' && (
          <div className="flex shrink-0 gap-0.5 opacity-100 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
            <IconButton label="Move to another day" onClick={() => setMoving(true)}><CalendarClock className="h-4 w-4" /></IconButton>
            <IconButton label="Skip" onClick={() => setTo('skipped')}><SkipForward className="h-4 w-4" /></IconButton>
          </div>
        )}
        {!readOnly && skipped && !details.missed && (
          <IconButton label="Undo skip" onClick={() => setTo('todo')}><Undo2 className="h-4 w-4" /></IconButton>
        )}
      </div>
      {moving && <MoveDialog task={task} onClose={() => setMoving(false)} />}
    </li>
  )
}

function TaskDetails({ details }: { details: Details }) {
  return (
    <div className="mt-2 space-y-2 rounded-md bg-subtle px-3 py-2.5 text-sm">
      {details.how && <p className="text-fg-muted">{details.how}</p>}
      {!!details.problems?.length && (
        <div>
          <p className="text-xs font-medium text-fg-muted">Suggested problems</p>
          <ul className="mt-1 space-y-0.5">
            {details.problems.map((p) => (
              <li key={p}>
                <a href={`https://leetcode.com/problemset/?search=${encodeURIComponent(p)}`} target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline">
                  {p} <ExternalLink className="h-3 w-3" aria-hidden />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        {details.interview && (
          <Link href={interviewHref(details.interview)} className="inline-flex items-center gap-1 font-medium text-primary hover:underline">
            <Mic className="h-3.5 w-3.5" aria-hidden /> Start the mock interview
          </Link>
        )}
        {details.resource && (
          <a href={details.resource.url} target={details.resource.url.startsWith('/') ? undefined : '_blank'} rel="noreferrer"
            className="inline-flex items-center gap-1 text-fg-muted hover:text-fg hover:underline">
            {details.resource.title} <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
        )}
      </div>
    </div>
  )
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} title={label} aria-label={label}
      className="rounded p-1.5 text-fg-subtle hover:bg-subtle hover:text-fg">
      {children}
    </button>
  )
}

function MoveDialog({ task, onClose }: { task: PlanTask; onClose: () => void }) {
  const move = useMoveTask()
  const [date, setDate] = useState(task.date)
  return (
    <Dialog open onClose={onClose} title="Move task" description={task.title}
      footer={<>
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button loading={move.isPending} onClick={() => move.mutate({ id: task.id, date }, { onSuccess: onClose })}>Move</Button>
      </>}>
      <Field label="New day" htmlFor="move-date" hint="The task stays on that day when the plan re-plans.">
        <Input id="move-date" type="date" min={isoDate()} value={date} onChange={(e) => setDate(e.target.value)} />
      </Field>
      {move.error && <Notice className="mt-3">{move.error.message}</Notice>}
    </Dialog>
  )
}
