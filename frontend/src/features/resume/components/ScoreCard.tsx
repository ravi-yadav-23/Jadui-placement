import type { SubScore } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { scoreColor } from './ui'

/** Overall score + every sub-score as a bar, each with "how is this calculated?". */
export default function ScoreCard({ title, score, subScores, footnote }: {
  title: string
  score: number
  subScores: SubScore[]
  footnote?: string
}) {
  return (
    <section className="card-base space-y-5" data-testid="score-card">
      <div className="flex items-end justify-between">
        <h2 className="text-lg font-semibold text-fg">{title}</h2>
        <p className={cn('text-5xl font-black', scoreColor(score))} data-testid="overall-score">
          {score}<span className="text-lg text-muted">/100</span>
        </p>
      </div>
      <ul className="space-y-3">
        {subScores.map((s) => (
          <li key={s.key}>
            <div className="flex justify-between text-sm">
              <span className="text-fg">{s.label}</span>
              <span className={scoreColor(s.score, s.max)}>{s.score} / {s.max}</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-surface">
              <div className="h-2 rounded-full bg-primary" style={{ width: `${(100 * s.score) / s.max}%` }} />
            </div>
            <details className="mt-1 text-xs text-muted">
              <summary className="cursor-pointer select-none">How is this calculated?</summary>
              <p className="mt-1">{s.explanation}</p>
            </details>
          </li>
        ))}
      </ul>
      {footnote && <p className="text-xs text-muted">{footnote}</p>}
    </section>
  )
}
