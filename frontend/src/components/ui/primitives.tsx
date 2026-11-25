/** Small building blocks used on every page. Plain elements + Tailwind; no component library. */
import type { HTMLAttributes, ReactNode } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('rounded-lg border border-border bg-surface shadow-xs', className)} {...props} />
}

export function CardHeader({ title, description, action, className }: {
  title: ReactNode; description?: ReactNode; action?: ReactNode; className?: string
}) {
  return (
    <div className={cn('flex items-start justify-between gap-4 border-b border-border px-5 py-4', className)}>
      <div className="min-w-0">
        <h2 className="text-md font-semibold">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-fg-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

type Tone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger'
const TONES: Record<Tone, string> = {
  neutral: 'bg-subtle text-fg-muted',
  primary: 'bg-primary-soft text-primary-soft-fg',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
}

export function Badge({ tone = 'neutral', className, ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return <span className={cn('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium', TONES[tone], className)} {...props} />
}

export function PageHeader({ title, description, actions }: { title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-fg-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  )
}

export function EmptyState({ icon, title, description, action, className }: {
  icon?: ReactNode; title: string; description?: string; action?: ReactNode; className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center rounded-lg border border-dashed border-border px-6 py-12 text-center', className)}>
      {icon && <div className="mb-3 text-fg-subtle">{icon}</div>}
      <p className="font-medium">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-fg-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function Progress({ value, max = 100, tone = 'primary', className, label }: {
  value: number; max?: number; tone?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral'; className?: string; label?: string
}) {
  const pct = Math.max(0, Math.min(100, (100 * value) / (max || 1)))
  const fill = { primary: 'bg-primary', success: 'bg-success', warning: 'bg-warning', danger: 'bg-danger', neutral: 'bg-fg-subtle' }[tone]
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-subtle', className)} role="progressbar"
      aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className={cn('h-full rounded-full transition-[width]', fill)} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function Stat({ label, value, hint, className }: { label: string; value: ReactNode; hint?: ReactNode; className?: string }) {
  return (
    <div className={className}>
      <p className="text-sm text-fg-muted">{label}</p>
      <p className="tabular mt-1 text-2xl font-semibold">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-fg-subtle">{hint}</p>}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-subtle', className)} />
}

export function Spinner({ label, className }: { label?: string; className?: string }) {
  return (
    <div className={cn('flex items-center gap-2 py-8 text-sm text-fg-muted', className)} role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {label}
    </div>
  )
}

export function Notice({ tone = 'danger', children, className }: { tone?: 'danger' | 'warning' | 'neutral' | 'primary'; children: ReactNode; className?: string }) {
  const style = { danger: 'border-danger/30 bg-danger-soft text-danger', warning: 'border-warning/30 bg-warning-soft text-warning',
    neutral: 'border-border bg-subtle text-fg-muted', primary: 'border-primary/30 bg-primary-soft text-primary-soft-fg' }[tone]
  return (
    <div className={cn('flex items-start gap-2 rounded-md border px-3 py-2.5 text-sm', style, className)} role={tone === 'danger' ? 'alert' : undefined}>
      {(tone === 'danger' || tone === 'warning') && <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />}
      <div className="min-w-0">{children}</div>
    </div>
  )
}

/** A tiny line chart for trends (position encodes value; NN/g: best for quick comparison). */
export function Sparkline({ values, max = 100, className }: { values: number[]; max?: number; className?: string }) {
  if (values.length < 2) return null
  const w = 120, h = 32
  const points = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - (v / max) * (h - 4) - 2}`).join(' ')
  const [lastX, lastY] = points.split(' ').at(-1)!.split(',')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={cn('h-8 w-[120px] overflow-visible', className)} aria-hidden>
      <polyline points={points} fill="none" stroke="rgb(var(--primary))" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lastX} cy={lastY} r="2.5" fill="rgb(var(--primary))" />
    </svg>
  )
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="rounded border border-border bg-subtle px-1.5 font-mono text-xs text-fg-muted">{children}</kbd>
}
