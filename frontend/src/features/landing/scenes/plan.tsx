'use client'

/** Walkthrough scenes for the planner: the questionnaire, the scheduler packing a week, and re-planning. */
import { ArrowRight, CalendarX, ClipboardCheck, Mic } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Chip, Reveal, useSteps } from '../motion'

export type SceneProps = { playing: boolean }

const QUESTIONS = [
  { q: 'Where are you right now?', options: ['College student', 'Working'], pick: 0 },
  { q: 'Which year?', options: ['1st', '2nd', '3rd', '4th'], pick: 3, note: 'asked only because you’re a student' },
  { q: 'What are you aiming for?', options: ['Service companies', 'Product companies', 'Top product'], pick: 1 },
  { q: 'Language for DSA', options: ['C++', 'Java', 'Python'], pick: 2 },
]

/** 1. Five short questions; later questions depend on earlier answers. */
export function ProfileScene({ playing }: SceneProps) {
  const step = useSteps(7, 850, playing)
  return (
    <div className="space-y-4">
      {QUESTIONS.map((item, i) => (
        <Reveal key={item.q} show={step >= i}>
          <p className="mb-1.5 text-xs font-medium">
            {item.q} {item.note && <span className="font-normal text-fg-subtle">({item.note})</span>}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {item.options.map((o, j) => <Chip key={o} selected={step > i && j === item.pick}>{o}</Chip>)}
          </div>
        </Reveal>
      ))}
      <Reveal show={step >= 4}>
        <p className="mb-1.5 text-xs font-medium">Hours you can study</p>
        <div className="space-y-1.5">
          {[['Weekdays', 2], ['Weekends', 5]].map(([label, hours]) => (
            <div key={label} className="grid grid-cols-[72px_1fr_36px] items-center gap-2 text-xs">
              <span className="text-fg-muted">{label}</span>
              <span className="h-2 overflow-hidden rounded-full bg-subtle">
                <span className="block h-full rounded-full bg-primary transition-[width] duration-700"
                  style={{ width: step >= 5 ? `${(Number(hours) / 6) * 100}%` : '0%' }} />
              </span>
              <span className="tabular text-right">{hours} h</span>
            </div>
          ))}
        </div>
      </Reveal>
      <Reveal show={step >= 6} className="rounded-md bg-primary-soft px-3 py-2 text-xs text-primary-soft-fg">
        20 h a week stated. The plan uses <b>85%</b> of it (17 h), because people overestimate their free time.
      </Reveal>
    </div>
  )
}

type Block = { day: number; label: string; minutes: number; kind: 'dsa' | 'cs' | 'project' | 'review' }
const BLOCKS: Block[] = [
  { day: 0, label: 'Arrays', minutes: 60, kind: 'dsa' }, { day: 0, label: 'OOP: classes', minutes: 40, kind: 'cs' },
  { day: 1, label: 'Arrays', minutes: 60, kind: 'dsa' }, { day: 1, label: 'DBMS: ER model', minutes: 40, kind: 'cs' },
  { day: 2, label: 'Strings', minutes: 60, kind: 'dsa' }, { day: 2, label: 'OS: processes', minutes: 25, kind: 'cs' },
  { day: 2, label: '', minutes: 15, kind: 'review' },
  { day: 3, label: 'Strings', minutes: 45, kind: 'dsa' }, { day: 3, label: 'DBMS: SQL', minutes: 40, kind: 'cs' },
  { day: 3, label: '', minutes: 15, kind: 'review' },
  { day: 4, label: 'Hashing', minutes: 60, kind: 'dsa' }, { day: 4, label: 'OOP: SOLID', minutes: 40, kind: 'cs' },
  { day: 5, label: 'Project: build the API', minutes: 150, kind: 'project' }, { day: 5, label: 'Hashing', minutes: 60, kind: 'dsa' },
  { day: 5, label: '', minutes: 15, kind: 'review' },
]
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const CAPACITY = [102, 102, 102, 102, 102, 255, 0] // 85% of 2 h on weekdays and 5 h on Saturday; Sunday is the rest day
const SCALE = 270 / 255 // px per minute
const KIND_STYLE: Record<Block['kind'], string> = {
  dsa: 'bg-primary text-primary-fg',
  cs: 'bg-primary-soft text-primary-soft-fg border border-primary/30',
  project: 'bg-fg/80 text-bg',
  review: 'border border-dashed border-primary bg-transparent text-primary',
}

/** 2. The scheduler fills each day up to its capacity: interleaved subjects, reviews, long work on weekends. */
export function ScheduleScene({ playing }: SceneProps) {
  const step = useSteps(BLOCKS.length + 2, 300, playing)
  return (
    <div>
      <div className="grid grid-cols-7 gap-1.5">
        {DAY_NAMES.map((day, d) => (
          <div key={day} className="flex flex-col items-stretch">
            <div className="flex h-[300px] flex-col justify-end">
              <span className="tabular mb-1 whitespace-nowrap text-center text-[10px] text-fg-subtle">
                {CAPACITY[d] ? `${(CAPACITY[d] / 60).toFixed(1)} h` : ''}
              </span>
              <div className={cn('flex flex-col gap-[3px] rounded-md border border-dashed p-[3px]',
                CAPACITY[d] ? 'border-border-strong/60' : 'border-transparent')}
                style={{ height: CAPACITY[d] ? CAPACITY[d] * SCALE + 6 : 40 }}>
                {!CAPACITY[d] && <span className="m-auto text-[10px] text-fg-subtle">Rest</span>}
                {BLOCKS.map((b, i) => b.day === d && (
                  <div key={i} title={b.label || 'Review'}
                    className={cn('overflow-hidden rounded-[4px] px-1 text-[9px] leading-[11px] transition-all duration-300 sm:text-[10px] sm:leading-3',
                      KIND_STYLE[b.kind], step > i ? 'scale-100 opacity-100' : 'scale-95 opacity-0')}
                    style={{ height: b.minutes * SCALE - 3, paddingTop: b.minutes >= 40 ? 3 : 1 }}>
                    {b.minutes >= 40 ? b.label : b.kind === 'review' ? 'Review' : ''}
                  </div>
                ))}
              </div>
            </div>
            <span className="mt-1.5 text-center text-[11px] text-fg-subtle">{day}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5 text-[11px] text-fg-muted">
        <Legend className="bg-primary">DSA</Legend>
        <Legend className="border border-primary/30 bg-primary-soft">CS subjects</Legend>
        <Legend className="bg-fg/80">Projects (weekends)</Legend>
        <Legend className="border border-dashed border-primary">Review after 2, 7, 21 days</Legend>
        <Legend className="border border-dashed border-border-strong/60">Usable time (85% of your hours)</Legend>
      </div>
      <Reveal show={step > BLOCKS.length} className="mt-3 text-xs text-fg-muted">
        {BLOCKS.length} tasks placed. No day goes over its time, and a topic starts only after the topics it needs.
      </Reveal>
    </div>
  )
}

function Legend({ className, children }: { className: string; children: string }) {
  return <span className="inline-flex items-center gap-1.5"><span className={cn('h-2.5 w-2.5 rounded-sm', className)} />{children}</span>
}

const EVENTS = [
  { icon: CalendarX, event: 'Missed: Indexing and B+ trees', effect: 'Kept in your history, placed again on Thursday' },
  { icon: ClipboardCheck, event: 'Check-in: 9 of 14 tasks done (64%)', effect: 'Next week plans with 54% of your hours (0.85 × 64%)' },
  { icon: Mic, event: 'Mock interview: DBMS scored 52', effect: 'Added a re-learn topic: Normalisation' },
  { icon: Mic, event: 'Mock interview: OS scored 81', effect: 'Closed the gap “CPU scheduling”' },
]

/** 6. Real life happens: missed days, check-ins and interview scores change the plan. */
export function AdaptScene({ playing }: SceneProps) {
  const step = useSteps(EVENTS.length * 2 + 1, 750, playing)
  return (
    <div>
    <ul className="space-y-3">
      {EVENTS.map(({ icon: Icon, event, effect }, i) => (
        <li key={event} className="grid items-center gap-2 sm:grid-cols-[1fr_auto_1fr]">
          <Reveal show={step >= i * 2} className="flex items-center gap-2.5 rounded-md border border-border bg-surface px-3 py-2.5 text-xs">
            <Icon className="h-4 w-4 shrink-0 text-fg-subtle" aria-hidden /> {event}
          </Reveal>
          <Reveal show={step >= i * 2 + 1} className="hidden text-primary sm:block"><ArrowRight className="h-4 w-4" aria-hidden /></Reveal>
          <Reveal show={step >= i * 2 + 1} className="rounded-md bg-primary-soft px-3 py-2.5 text-xs text-primary-soft-fg">{effect}</Reveal>
        </li>
      ))}
    </ul>
    <Reveal show={step > EVENTS.length * 2} className="mt-6 border-t border-border pt-4 text-xs text-fg-muted">
      One re-plan step handles all of these: past days stay as history, and the next 14 days are rebuilt from what&apos;s
      left, your real pace and your newest scores.
    </Reveal>
    </div>
  )
}
