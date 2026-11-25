'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'

import type { Check } from '@/lib/api/types'

const ORDER = { fail: 0, warn: 1, info: 2, pass: 3 } as const
const ICON = {
  fail: <XCircle className="h-4 w-4 text-error" />,
  warn: <AlertTriangle className="h-4 w-4 text-warning" />,
  info: <Info className="h-4 w-4 text-accent" />,
  pass: <CheckCircle2 className="h-4 w-4 text-success" />,
}

/** "Can a parser read this file?" - problems first, passes collapsed. */
export default function ParseHealthPanel({ checks, rawText }: { checks: Check[]; rawText?: string | null }) {
  const [showText, setShowText] = useState(false)
  const sorted = [...checks].sort((a, b) => ORDER[a.status] - ORDER[b.status])
  const problems = sorted.filter((c) => c.status !== 'pass')
  const passes = sorted.filter((c) => c.status === 'pass')

  return (
    <section className="card-base space-y-4" data-testid="parse-health">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-fg">Parse health</h2>
        <span className="text-sm text-muted">{passes.length}/{checks.length} checks passed</span>
      </div>
      <p className="text-xs text-muted">
        How reliably a parser (and a recruiter skimming plain text) can read your file. No tool can see a
        company&apos;s real ATS settings; these are the problems that commonly break parsing.
      </p>

      <ul className="space-y-2">
        {problems.map((check) => (
          <li key={check.id} className="rounded-lg border border-border bg-surface/50 p-3">
            <div className="flex items-center gap-2 text-sm text-fg">{ICON[check.status]} {check.message}</div>
            {check.fix && <p className="ml-6 mt-1 text-xs text-muted">Fix: {check.fix}</p>}
          </li>
        ))}
      </ul>

      {passes.length > 0 && (
        <details className="text-sm text-muted">
          <summary className="cursor-pointer">{passes.length} passed checks</summary>
          <ul className="mt-2 space-y-1">
            {passes.map((check) => (
              <li key={check.id} className="flex items-center gap-2">{ICON.pass} {check.message}</li>
            ))}
          </ul>
        </details>
      )}

      {rawText && (
        <div>
          <button className="text-sm text-primary hover:underline" onClick={() => setShowText((v) => !v)}>
            {showText ? 'Hide' : 'Show'} the text a parser extracts
          </button>
          {showText && (
            <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-surface p-3 text-xs text-muted">
              {rawText}
            </pre>
          )}
        </div>
      )}
    </section>
  )
}
