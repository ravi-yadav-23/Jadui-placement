'use client'

import { useState } from 'react'
import { Copy, HelpCircle, ShieldCheck, Sparkles } from 'lucide-react'

import type { BulletFeedback, GeneralReview } from '@/lib/api/types'
import ScoreCard from './ScoreCard'

export const ISSUE_LABELS: Record<string, string> = {
  no_metric: 'No number / result',
  weak_start: 'Weak opening verb',
  pronoun: 'Uses I / my / we',
  passive: 'Passive voice',
  length: 'Too short or too long',
  buzzword: 'Buzzword',
  vague: 'Vague wording',
  low_depth: 'Little technical depth',
  unclear_outcome: 'Outcome unclear',
  jargon: 'Jargon',
}

/** Renders "[X]" placeholders highlighted, so the user sees what they must fill in. */
export function WithPlaceholders({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\[X\])/).map((part, i) =>
        part === '[X]' ? <mark key={i} className="rounded bg-warning/20 px-1 text-warning">[X]</mark> : part)}
    </>
  )
}

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
      onClick={() => navigator.clipboard.writeText(text).then(() => setCopied(true))}
    >
      <Copy className="h-3 w-3" /> {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function BulletCard({ bullet }: { bullet: BulletFeedback }) {
  return (
    <li className="rounded-lg border border-border bg-surface/40 p-4" data-testid="bullet-feedback">
      <p className="text-xs text-muted">{bullet.entry_title ?? bullet.section}</p>
      <p className="mt-1 text-sm text-white">{bullet.text}</p>
      {bullet.issues && bullet.issues.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {bullet.issues.map((issue) => (
            <span key={issue} className="rounded-full border border-warning/30 bg-warning/10 px-2 py-0.5 text-xs text-warning">
              {ISSUE_LABELS[issue] ?? issue}
            </span>
          ))}
        </div>
      )}
      {bullet.rewrite && (
        <div className="mt-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1 text-xs font-medium text-primary">
              <Sparkles className="h-3 w-3" /> Suggested rewrite
            </span>
            <CopyButton text={bullet.rewrite} />
          </div>
          <p className="mt-1 text-sm text-white"><WithPlaceholders text={bullet.rewrite} /></p>
        </div>
      )}
      {bullet.coach_questions && bullet.coach_questions.length > 0 && (
        <ul className="mt-2 space-y-1">
          {bullet.coach_questions.map((q) => (
            <li key={q} className="flex items-start gap-1 text-xs text-accent"><HelpCircle className="mt-0.5 h-3 w-3" /> {q}</li>
          ))}
        </ul>
      )}
    </li>
  )
}

export default function GeneralReviewView({ review }: { review: GeneralReview }) {
  const needsWork = review.bullets.filter((b) => b.rewrite || (b.issues?.length ?? 0) > 0)
  const fine = review.bullets.filter((b) => !needsWork.includes(b))

  return (
    <div className="space-y-6">
      <ScoreCard
        title="Resume review"
        score={review.overall_score}
        subScores={review.sub_scores}
        footnote="75 of 100 points are counted by rules; only Substance uses AI ratings. Your name and contact details are never sent to the AI."
      />

      {(review.top_actions?.length ?? 0) > 0 && (
        <section className="card-base">
          <h2 className="text-lg font-semibold text-white">Top fixes</h2>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-white">
            {review.top_actions?.map((a) => <li key={a}>{a}</li>)}
          </ol>
          {(review.strengths?.length ?? 0) > 0 && (
            <p className="mt-3 text-sm text-muted">Strengths: {review.strengths?.join(' · ')}</p>
          )}
        </section>
      )}

      {(review.findings?.length ?? 0) > 0 && (
        <section className="card-base space-y-2">
          <h2 className="text-lg font-semibold text-white">Resume-wide findings</h2>
          {review.findings?.map((f) => <p key={f.code} className="text-sm text-warning">{f.message}</p>)}
        </section>
      )}

      <section className="card-base space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Bullet by bullet</h2>
          <span className="flex items-center gap-1 text-xs text-muted">
            <ShieldCheck className="h-3 w-3 text-success" /> Rewrites never add facts; [X] = fill in your real number
          </span>
        </div>
        <ul className="space-y-3">{needsWork.map((b) => <BulletCard key={b.bullet_id} bullet={b} />)}</ul>
        {fine.length > 0 && (
          <details className="text-sm text-muted">
            <summary className="cursor-pointer">{fine.length} strong bullet(s), no changes suggested</summary>
            <ul className="mt-2 space-y-3">{fine.map((b) => <BulletCard key={b.bullet_id} bullet={b} />)}</ul>
          </details>
        )}
        {(review.ungrounded_count ?? 0) > 0 && (
          <p className="text-xs text-muted">{review.ungrounded_count} extracted bullet(s) didn&apos;t match your file and were skipped.</p>
        )}
      </section>
    </div>
  )
}
