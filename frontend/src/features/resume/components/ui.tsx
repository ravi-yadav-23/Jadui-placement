/** Shared helpers for the resume and interview pages, built on the app's UI kit. */
import Link from 'next/link'
import { Loader2 } from 'lucide-react'

import { Badge, Notice, Spinner as BaseSpinner } from '@/components/ui'
import { ApiError } from '@/lib/api/client'
import { TONE_TEXT, scoreTone } from '@/lib/utils'

const STATUS_TONE: Record<string, 'success' | 'danger' | 'primary'> = {
  ready: 'success', done: 'success', failed: 'danger', queued: 'primary', processing: 'primary', running: 'primary',
}

export function StatusBadge({ status }: { status: string }) {
  const working = status === 'queued' || status === 'processing' || status === 'running'
  return (
    <Badge tone={STATUS_TONE[status] ?? 'neutral'}>
      {working && <Loader2 className="h-3 w-3 animate-spin" aria-hidden />}
      {working ? 'processing' : status}
    </Badge>
  )
}

export function Spinner({ label }: { label: string }) {
  return <BaseSpinner label={label} />
}

/** Shows an API error; for 401 it links to sign-in instead. */
export function ErrorBox({ error }: { error: unknown }) {
  if (error instanceof ApiError && error.status === 401) {
    return <Notice tone="neutral">Please <Link href="/auth/login" className="text-primary underline">sign in</Link> to continue.</Notice>
  }
  return <Notice>{error instanceof Error ? error.message : 'Something went wrong.'}</Notice>
}

export function scoreColor(score: number, max = 100) {
  return TONE_TEXT[scoreTone(score, max)]
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
