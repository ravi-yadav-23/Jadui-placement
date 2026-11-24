'use client'

import Link from 'next/link'
import { ArrowLeft, Flag, RotateCcw, SkipForward } from 'lucide-react'

import AnswerBox from '@/features/interview/components/AnswerBox'
import InterviewReport from '@/features/interview/components/InterviewReport'
import TurnFeedback from '@/features/interview/components/TurnFeedback'
import { useAnswer, useFinish, useInterview, useRetry, useSkip } from '@/features/interview/hooks'
import { TRACKS } from '@/features/interview/labels'
import { ErrorBox, Spinner } from '@/features/resume/components/ui'

/** A running interview (one question at a time), or its report once completed. Refresh-safe: state lives on the server. */
export default function InterviewSessionPage({ params }: { params: { interviewId: string } }) {
  const id = params.interviewId
  const interview = useInterview(id)
  const answer = useAnswer(id)
  const skip = useSkip(id)
  const finish = useFinish(id)
  const retry = useRetry(id)
  const data = interview.data
  const actionError = answer.error || skip.error || finish.error || retry.error

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link href="/dashboard/interview" className="flex items-center gap-1 text-sm text-muted hover:text-white">
        <ArrowLeft className="h-4 w-4" /> All interviews
      </Link>

      {interview.isLoading && <Spinner label="Loading…" />}
      {interview.error && <ErrorBox error={interview.error} />}
      {data?.status === 'planning' && <Spinner label="Planning your questions…" />}
      {data?.status === 'failed' && <ErrorBox error={new Error(data.error || 'This interview could not start.')} />}
      {data?.status === 'completed' && data.report && <InterviewReport interview={data} report={data.report} />}

      {data?.status === 'active' && (() => {
        const current = data.turns[data.turns.length - 1]
        const earlier = data.turns.slice(0, -1)
        const lastFeedback = [...earlier].reverse().find((t) => t.evaluation)?.evaluation
        const busy = answer.isPending || skip.isPending || finish.isPending
        return (
          <>
            <header className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-white">{TRACKS[data.track].label}</span>
                <span className="text-muted" data-testid="progress">Question {data.question_number} of {data.question_count}</span>
              </div>
              <div className="h-1.5 rounded-full bg-surface">
                <div className="h-1.5 rounded-full bg-primary transition-all"
                  style={{ width: `${(100 * (data.question_number - 1)) / data.question_count}%` }} />
              </div>
            </header>

            {data.mode === 'practice' && lastFeedback && current.status === 'asked' && (
              <section className="card-base border-primary/30">
                <h2 className="mb-2 text-sm font-semibold text-primary">Feedback on your last answer</h2>
                <TurnFeedback evaluation={lastFeedback} />
              </section>
            )}

            {current.kind === 'follow_up' && <p className="text-sm font-medium text-primary">Follow-up question</p>}

            {current.status === 'asked' && (
              <AnswerBox question={current.question} turnKey={current.id} busy={busy}
                onSubmit={(body) => answer.mutate({ turnId: current.id, body })} />
            )}

            {current.status === 'evaluating' && (
              <section className="card-base space-y-3">
                <p className="font-medium text-white">{current.question}</p>
                <p className="whitespace-pre-wrap text-sm text-white/70">{current.answer}</p>
                <Spinner label="The interviewer is reviewing your answer…" />
              </section>
            )}

            {current.status === 'failed' && (
              <section className="card-base space-y-3">
                <ErrorBox error={new Error(current.error || 'Could not evaluate your answer.')} />
                <button onClick={() => retry.mutate(current.id)} className="btn-outline flex items-center gap-2">
                  <RotateCcw className="h-4 w-4" /> Retry evaluation
                </button>
              </section>
            )}

            {actionError && <ErrorBox error={actionError} />}

            <div className="flex justify-between">
              <button onClick={() => skip.mutate(undefined)} disabled={busy || current.status !== 'asked'}
                className="flex items-center gap-1 text-sm text-muted hover:text-white disabled:opacity-40">
                <SkipForward className="h-4 w-4" /> Skip question
              </button>
              <button onClick={() => confirm('End the interview now? Unanswered questions are left out of the report.')
                && finish.mutate(undefined)}
                disabled={busy || current.status === 'evaluating'} data-testid="finish-interview"
                className="flex items-center gap-1 text-sm text-muted hover:text-error disabled:opacity-40">
                <Flag className="h-4 w-4" /> End interview
              </button>
            </div>

            {earlier.length > 0 && (
              <details className="card-base text-sm">
                <summary className="cursor-pointer select-none text-muted">Earlier in this interview ({earlier.length})</summary>
                <ul className="mt-3 space-y-3">
                  {earlier.map((t) => (
                    <li key={t.id} className="border-l-2 border-border pl-3">
                      <p className="text-white">{t.kind === 'follow_up' ? 'Follow-up: ' : ''}{t.question}</p>
                      <p className="mt-1 whitespace-pre-wrap text-white/60">{t.status === 'skipped' ? '(skipped)' : t.answer}</p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        )
      })()}
    </div>
  )
}
