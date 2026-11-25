'use client'

import Link from 'next/link'
import { Trash2 } from 'lucide-react'

import { cn } from '@/lib/utils'
import { ErrorBox, Spinner, formatDate, scoreColor } from '@/features/resume/components/ui'
import { useDeleteInterview, useInterviews } from '../hooks'
import { TRACKS } from '../labels'

/** Past interviews, newest first, with a per-track trend (oldest -> newest score). */
export default function HistoryList() {
  const interviews = useInterviews()
  const remove = useDeleteInterview()
  const items = interviews.data ?? []

  const trends: Record<string, number[]> = {}
  for (const item of [...items].reverse()) {
    if (item.status === 'completed' && item.score != null) (trends[item.track] ??= []).push(item.score)
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-fg">Your interviews</h2>
      {interviews.isLoading && <Spinner label="Loading…" />}
      {interviews.error && <ErrorBox error={interviews.error} />}
      {interviews.data?.length === 0 && <p className="text-sm text-muted">No interviews yet. Start one above.</p>}

      {Object.keys(trends).length > 0 && (
        <ul className="flex flex-wrap gap-3 text-xs text-muted">
          {Object.entries(trends).map(([track, scores]) => (
            <li key={track} className="rounded-lg border border-border px-3 py-1.5">
              {TRACKS[track as keyof typeof TRACKS]?.label ?? track}: <span className="text-fg">{scores.slice(-5).join(' → ')}</span>
            </li>
          ))}
        </ul>
      )}

      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.id} className="card-base flex items-center justify-between gap-3 p-3">
            <Link href={`/dashboard/interview/${item.id}`} className="min-w-0 flex-1 text-sm text-fg hover:text-primary">
              {TRACKS[item.track]?.label ?? item.track}
              {item.target_role && <span className="text-muted"> · {item.target_role}</span>}
              <span className="ml-2 text-xs text-muted">{formatDate(item.created_at)}</span>
            </Link>
            {item.status === 'completed' && item.score != null
              ? <span className={cn('font-bold', scoreColor(item.score))}>{item.score}</span>
              : <span className="text-xs text-muted">{item.status === 'active' ? 'in progress' : item.status}</span>}
            <button title="Delete interview" className="text-muted hover:text-error"
              onClick={() => confirm('Delete this interview and its feedback?') && remove.mutate(item.id)}>
              <Trash2 className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
