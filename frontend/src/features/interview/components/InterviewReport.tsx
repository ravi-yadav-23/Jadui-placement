import Link from 'next/link'
import { Check, SkipForward, X } from 'lucide-react'

import type { InterviewDetail, InterviewReport as Report } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { scoreColor } from '@/features/resume/components/ui'
import { BANDS, SCORE_FORMULA, topicLabel } from '../labels'
import TurnFeedback from './TurnFeedback'

/** End-of-interview report: score, dimensions, topics, every question with its answers, delivery, gaps. */
export default function InterviewReport({ interview, report }: { interview: InterviewDetail; report: Report }) {
  const band = BANDS[report.band]
  return (
    <div className="space-y-6" data-testid="interview-report">
      <section className="card-base space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Interview score</h2>
            <p className={cn('text-sm font-medium', band.style)}>{band.label}</p>
          </div>
          <p className={cn('text-5xl font-black', scoreColor(report.score))} data-testid="interview-score">
            {report.score}<span className="text-lg text-muted">/100</span>
          </p>
        </div>
        <details className="text-xs text-muted">
          <summary className="cursor-pointer select-none">How is this calculated?</summary>
          <p className="mt-1">{SCORE_FORMULA}</p>
        </details>

        <div className="grid gap-6 sm:grid-cols-2">
          {Object.keys(report.dimensions).length > 0 && (
            <Bars title="Dimensions (1-5)" entries={Object.entries(report.dimensions)} max={5} />
          )}
          {Object.keys(report.topics).length > 0 && (
            <Bars title="Topics (0-100)" entries={Object.entries(report.topics).map(([t, s]) => [topicLabel(t), s])}
              max={100} />
          )}
        </div>
      </section>

      {(report.gaps ?? []).length > 0 && (
        <section className="card-base">
          <h3 className="font-semibold text-white">What to work on</h3>
          <p className="mt-1 text-xs text-muted">Saved as skill gaps; the task planner will turn them into tasks.</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {(report.gaps ?? []).map((gap) => (
              <li key={gap} className="rounded-full border border-warning/40 bg-warning/10 px-3 py-1 text-xs text-warning">{gap}</li>
            ))}
          </ul>
        </section>
      )}

      {report.delivery && (
        <section className="card-base text-sm">
          <h3 className="font-semibold text-white">Delivery ({report.delivery.voice_answers} spoken answers)</h3>
          <p className="mt-1 text-xs text-muted">Information only, not part of the score.</p>
          <ul className="mt-3 grid gap-2 sm:grid-cols-3">
            <li>Pace: <b className="text-white">{report.delivery.wpm ?? 'n/a'}</b> words/min <span className="text-xs text-muted">(120-160 is comfortable)</span></li>
            <li>Filler words: <b className="text-white">{report.delivery.fillers_per_100_words}</b> per 100 words</li>
            <li>Repeated: <b className="text-white">{report.delivery.repeated.join(', ') || 'none'}</b></li>
          </ul>
        </section>
      )}

      <section className="space-y-3">
        <h3 className="text-lg font-semibold text-white">Question by question</h3>
        {report.questions.length === 0 && <p className="text-sm text-muted">No questions were answered.</p>}
        {report.questions.map((q, i) => {
          const turns = interview.turns.filter((t) => t.question_id === q.question_id)
          return (
            <details key={q.question_id} className="card-base" open={i === 0}>
              <summary className="flex cursor-pointer select-none items-start justify-between gap-4">
                <span className="text-sm text-white">
                  <span className="mr-2 text-xs uppercase text-muted">{topicLabel(q.topic)}</span>{q.question}
                </span>
                {q.skipped
                  ? <span className="flex items-center gap-1 text-xs text-muted"><SkipForward className="h-3 w-3" /> skipped</span>
                  : <span className={cn('font-bold', scoreColor(q.score))}>{q.score}</span>}
              </summary>
              <div className="mt-4 space-y-4">
                {turns.filter((t) => t.answer).map((t) => (
                  <div key={t.id} className="space-y-2 border-l-2 border-border pl-3">
                    {t.kind === 'follow_up' && <p className="text-sm font-medium text-primary">Follow-up: {t.question}</p>}
                    <p className="whitespace-pre-wrap text-sm text-white/80">{t.answer}</p>
                    {t.evaluation && <TurnFeedback evaluation={t.evaluation} />}
                  </div>
                ))}
                <div className="rounded-lg bg-surface p-3 text-sm">
                  <p className="font-medium text-white">A strong answer covers</p>
                  <ul className="mt-2 space-y-1">
                    {(q.covered ?? []).map((c) => <li key={c.point} className="flex gap-2"><Check className="h-4 w-4 shrink-0 text-success" />{c.point}</li>)}
                    {(q.missed ?? []).map((p) => <li key={p} className="flex gap-2"><X className="h-4 w-4 shrink-0 text-error" />{p}</li>)}
                  </ul>
                </div>
              </div>
            </details>
          )
        })}
      </section>

      <Link href="/dashboard/interview" className="btn-outline inline-block">Start another interview</Link>
    </div>
  )
}

function Bars({ title, entries, max }: { title: string; entries: [string, number][]; max: number }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-white">{title}</h3>
      <ul className="space-y-2">
        {entries.map(([name, value]) => (
          <li key={name}>
            <div className="flex justify-between text-xs">
              <span className="text-white">{name}</span>
              <span className={scoreColor(value, max)}>{value}</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-surface">
              <div className="h-2 rounded-full bg-primary" style={{ width: `${(100 * value) / max}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
