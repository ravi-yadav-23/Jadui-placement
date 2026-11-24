/** Small shared pieces for the resume screener pages. */
import Link from 'next/link'
import { AlertTriangle, Loader2 } from 'lucide-react'

import { ApiError } from '@/lib/api/client'
import { cn } from '@/lib/utils'

const STATUS_STYLE: Record<string, string> = {
  ready: 'bg-success/10 text-success border-success/30',
  done: 'bg-success/10 text-success border-success/30',
  failed: 'bg-error/10 text-error border-error/30',
  queued: 'bg-primary/10 text-primary border-primary/30',
  processing: 'bg-primary/10 text-primary border-primary/30',
  running: 'bg-primary/10 text-primary border-primary/30',
}

export function StatusBadge({ status }: { status: string }) {
  const working = status === 'queued' || status === 'processing' || status === 'running'
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium',
      STATUS_STYLE[status] ?? 'border-border text-muted')}>
      {working && <Loader2 className="h-3 w-3 animate-spin" />}
      {working ? 'processing' : status}
    </span>
  )
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-muted">
      <Loader2 className="h-5 w-5 animate-spin text-primary" /> {label}
    </div>
  )
}

/** Shows an API error; for 401 it links to sign-in instead. */
export function ErrorBox({ error }: { error: unknown }) {
  if (error instanceof ApiError && error.status === 401) {
    return (
      <div className="card-base text-sm text-muted">
        Please <Link href="/auth/login" className="text-primary underline">sign in</Link> to use the resume screener.
      </div>
    )
  }
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div className="flex items-start gap-2 rounded-lg border border-error/30 bg-error/10 p-3 text-sm text-error">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {message}
    </div>
  )
}

export function scoreColor(score: number, max = 100) {
  const ratio = score / max
  if (ratio >= 0.75) return 'text-success'
  if (ratio >= 0.5) return 'text-warning'
  return 'text-error'
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
