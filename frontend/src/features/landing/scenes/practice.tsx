'use client'

/** Walkthrough scenes for practice: a scored mock interview, the resume review, and the coach. */
import { AlertTriangle, Ban, Check, CornerDownRight, EyeOff } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Reveal, useSteps } from '../motion'
import type { SceneProps } from './plan'

// The answer is split into pieces so the quoted evidence can be highlighted when a key point is checked.
const ANSWER: [string, number?][] = [
  ['The OS '], ['saves the registers and program counter', 0], [' of the running process in its PCB. '],
  ['The scheduler picks the next process and '], ['loads its saved state', 1], ['. This happens '],
  ['on interrupts or system calls', 2], ['.'],
]
const SENTENCE_END = [3, 6, 8] // the answer appears one sentence per step
const POINTS = ['Saves CPU state to the PCB', 'Loads the next process’s state', 'Triggered by interrupts or system calls',
  'Switching has a cost (no useful work, caches go cold)']

/** 3. A mock interview: key points only count when the judge can quote your words. */
export function InterviewScene({ playing }: SceneProps) {
  const step = useSteps(9, 850, playing)
  const sentences = step >= 3 ? 3 : step
  const shownPieces = sentences ? SENTENCE_END[sentences - 1] : 0
  const checked = (i: number) => step >= 4 + i
  return (
    <div className="grid gap-4 md:grid-cols-[1.15fr_1fr]">
      <div className="space-y-3">
        <div className="rounded-md border border-border bg-subtle px-3 py-2.5">
          <p className="text-[11px] text-fg-subtle">Question 3 of 6 · Operating systems</p>
          <p className="mt-0.5 text-sm font-medium">What happens during a context switch?</p>
        </div>
        <div className="min-h-[96px] rounded-md border border-border px-3 py-2.5 text-[13px] leading-relaxed">
          <p className="mb-1 text-[11px] text-fg-subtle">Your answer</p>
          {ANSWER.slice(0, shownPieces).map(([text, point], i) => (
            <span key={i} className={cn('rounded-sm transition-colors duration-500',
              point !== undefined && checked(point) && 'bg-primary-soft text-primary-soft-fg')}>{text}</span>
          ))}
        </div>
        <Reveal show={step >= 7} className="flex gap-2 rounded-md border border-border px-3 py-2.5 text-[13px]">
          <CornerDownRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
          <span><span className="text-[11px] text-fg-subtle">Follow-up (one at most)</span><br />Why do systems try to keep context switches rare?</span>
        </Reveal>
      </div>
      <div className="space-y-3">
        <div className="rounded-md border border-border px-3 py-2.5">
          <p className="mb-2 text-[11px] text-fg-subtle">Key points a strong answer covers</p>
          <ul className="space-y-2">
            {POINTS.map((p, i) => {
              const missed = i === 3 && step >= 7
              return (
                <li key={p} className="flex items-start gap-2 text-xs">
                  <span className={cn('mt-px grid h-4 w-4 shrink-0 place-items-center rounded-full border transition-colors duration-300',
                    checked(i) && i < 3 ? 'border-primary bg-primary text-primary-fg' : missed ? 'border-warning text-warning' : 'border-border-strong')}>
                    {checked(i) && i < 3 && <Check className="h-2.5 w-2.5" />}
                    {missed && <span className="text-[9px] font-bold">!</span>}
                  </span>
                  <span className={cn(missed && 'text-warning')}>{p}{missed && ' (not covered)'}</span>
                </li>
              )
            })}
          </ul>
        </div>
        <Reveal show={step >= 8} className="rounded-md border border-border px-3 py-2.5">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] text-fg-subtle">Score for this answer</span>
            <span className="tabular text-2xl font-semibold">78</span>
          </div>
          <p className="tabular mt-1 font-mono text-[11px] text-fg-muted">0.6 × rubric 80 + 0.4 × key points 75</p>
        </Reveal>
      </div>
    </div>
  )
}

const CHECKS = [
  { ok: true, text: 'Two-column layout read in the right order' },
  { ok: true, text: 'Name, email and phone removed before any AI call' },
  { ok: false, text: '3 bullets describe duties, not outcomes' },
]

/** 4. The resume review: parse checks, then rewrites that may never add facts. */
export function ResumeScene({ playing }: SceneProps) {
  const step = useSteps(8, 850, playing)
  return (
    <div className="grid gap-4 md:grid-cols-[180px_1fr]">
      <div className="relative hidden overflow-hidden rounded-md border border-border bg-surface p-3 md:block" aria-hidden>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-20 rounded-sm bg-fg/70" />
          {step >= 2 && <EyeOff className="h-3 w-3 text-primary" />}
        </div>
        <span className="mt-1.5 block h-1.5 w-28 rounded-sm bg-subtle" />
        <div className="mt-3 grid grid-cols-[1fr_2fr] gap-2">
          <div className="space-y-1.5">{[...Array(9)].map((_, i) => <span key={i} className="block h-1.5 rounded-sm bg-subtle" />)}</div>
          <div className="space-y-1.5">
            {[...Array(14)].map((_, i) => (
              <span key={i} className={cn('block h-1.5 rounded-sm transition-colors duration-500',
                i === 5 && step >= 4 ? 'bg-warning/60' : 'bg-subtle', i % 4 === 0 && 'w-2/3')} />
            ))}
          </div>
        </div>
        {step < 3 && <span className="absolute inset-x-0 h-0.5 animate-scan bg-primary/70" />}
      </div>

      <div className="space-y-2.5">
        <ul className="space-y-1.5">
          {CHECKS.map((c, i) => (
            <Reveal as="li" key={c.text} show={step >= i + 1} className="flex items-center gap-2 text-xs">
              {c.ok ? <Check className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
                : <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warning" aria-hidden />}
              {c.text}
            </Reveal>
          ))}
        </ul>
        <Reveal show={step >= 4} className="rounded-md border border-border px-3 py-2 text-xs">
          <span className="text-[11px] text-fg-subtle">Your bullet</span>
          <p className="mt-0.5">Worked on backend for the college fest app.</p>
        </Reveal>
        <Reveal show={step >= 5} className={cn('rounded-md border px-3 py-2 text-xs transition-colors duration-500',
          step >= 6 ? 'border-danger/40 bg-danger-soft' : 'border-border')}>
          <span className="flex items-center justify-between text-[11px] text-fg-subtle">
            AI draft {step >= 6 && <span className="inline-flex items-center gap-1 font-medium text-danger"><Ban className="h-3 w-3" aria-hidden /> Blocked</span>}
          </span>
          <p className={cn('mt-0.5', step >= 6 && 'text-fg-muted line-through')}>Built REST APIs serving 5,000+ students for the fest app.</p>
          {step >= 6 && <p className="mt-1 text-[11px] text-danger">“5,000+” is not in your resume, so it can’t be suggested.</p>}
        </Reveal>
        <Reveal show={step >= 7} className="rounded-md border border-primary/40 bg-primary-soft px-3 py-2 text-xs text-primary-soft-fg">
          <span className="text-[11px] opacity-80">Suggested</span>
          <p className="mt-0.5 font-medium">Built the REST API for the college fest app.</p>
          <p className="mt-1 text-[11px] opacity-90">How many students used it? Add the number yourself if you know it.</p>
        </Reveal>
      </div>
    </div>
  )
}

/** 5. The coach answers from your data and proposes actions; nothing runs until you click. */
export function CoachScene({ playing }: SceneProps) {
  const step = useSteps(6, 1000, playing)
  return (
    <div className="flex min-h-[300px] flex-col gap-3">
      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-fg-subtle">
        Reads:
        {['your plan', 'today’s tasks', 'interview scores', 'skill gaps', 'resume review'].map((s) => (
          <span key={s} className="rounded border border-border px-1.5 py-0.5">{s}</span>
        ))}
      </div>
      <div className="ml-auto max-w-[80%] rounded-lg rounded-br-sm bg-primary px-3 py-2 text-[13px] text-primary-fg">
        I missed DBMS yesterday. What should I do today?
      </div>
      {step === 1 && (
        <div className="flex w-14 gap-1 rounded-lg bg-subtle px-3 py-3" aria-label="Coach is typing">
          {[0, 1, 2].map((i) => <span key={i} className="h-1.5 w-1.5 animate-dot rounded-full bg-fg-muted" style={{ animationDelay: `${i * 0.15}s` }} />)}
        </div>
      )}
      <Reveal show={step >= 2} className={cn('max-w-[88%] rounded-lg rounded-bl-sm border border-border px-3 py-2 text-[13px]', step < 2 && 'hidden')}>
        Yesterday&apos;s <b>Indexing and B+ trees</b> (45 min) is still open. Today already has 1 h 40 min planned, so it
        won&apos;t fit. Saturday has 1 h 30 min free.
      </Reveal>
      <Reveal show={step >= 3} className="flex flex-wrap gap-2">
        <span className={cn('inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium transition-all duration-200',
          step >= 4 ? 'border-primary bg-primary text-primary-fg ring-2 ring-primary/30' : 'border-border bg-surface')}>
          Move “Indexing” to Saturday
        </span>
        <span className="inline-flex h-8 items-center rounded-md border border-border bg-surface px-3 text-xs font-medium">
          Start a DBMS mock interview
        </span>
      </Reveal>
      <Reveal show={step >= 5} className="mt-auto flex items-center gap-2 rounded-md bg-subtle px-3 py-2 text-xs text-fg-muted">
        <Check className="h-3.5 w-3.5 text-primary" aria-hidden /> Moved to Saturday. The coach only suggests; you clicked.
      </Reveal>
    </div>
  )
}
