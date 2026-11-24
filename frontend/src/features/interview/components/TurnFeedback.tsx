import { Check, X } from 'lucide-react'

import type { TurnEvaluation } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { scoreColor } from '@/features/resume/components/ui'

/** Feedback on one answer: the judge's comment, each dimension's anchor, and key points with quotes. */
export default function TurnFeedback({ evaluation, compact = false }: { evaluation: TurnEvaluation; compact?: boolean }) {
  return (
    <div className="space-y-3 text-sm" data-testid="turn-feedback">
      <div className="flex items-start justify-between gap-4">
        <p className="text-white/90">{evaluation.feedback}</p>
        <span className={cn('shrink-0 text-xl font-bold', scoreColor(evaluation.score))}>{evaluation.score}</span>
      </div>

      {!compact && evaluation.dimensions.length > 0 && (
        <ul className="grid gap-2 sm:grid-cols-2">
          {evaluation.dimensions.map((d) => (
            <li key={d.name} className="rounded-lg border border-border p-2">
              <div className="flex justify-between text-xs">
                <span className="font-medium capitalize text-white">{d.name}</span>
                <span className={scoreColor(d.anchor, 5)}>{d.anchor} / 5</span>
              </div>
              <p className="mt-1 text-xs text-muted">{d.reason}</p>
            </li>
          ))}
        </ul>
      )}

      <ul className="space-y-1.5">
        {evaluation.covered.map((c) => (
          <li key={c.point} className="flex gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
            <span>
              <span className="text-white">{c.point}</span>
              <span className="block text-xs italic text-muted">You said: “{c.quote}”</span>
            </span>
          </li>
        ))}
        {evaluation.missed.map((point) => (
          <li key={point} className="flex gap-2">
            <X className="mt-0.5 h-4 w-4 shrink-0 text-error" />
            <span className="text-white/80">{point}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
