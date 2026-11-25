'use client'

import { Bot, Calendar, Check, FileText, LayoutDashboard, Mic, Settings } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Frame, useInView, useSteps } from './motion'

const NAV = [
  [LayoutDashboard, 'Today'], [Calendar, 'Planner'], [Mic, 'Interviews'], [FileText, 'Resume'], [Bot, 'Coach'], [Settings, 'Settings'],
] as const

const TASKS = [
  { title: 'Sliding window: 2 problems in Python', meta: 'DSA · Practice · 1 h', minutes: 60, at: 2 },
  { title: 'Review: Deadlocks', meta: 'OS · Review · 15 min', minutes: 15, at: 4 },
  { title: 'Indexing and B+ trees', meta: 'DBMS · Learn · 45 min', minutes: 45, at: 6 },
  { title: 'Fest app: write the API tests', meta: 'Projects · Project · 30 min', minutes: 30, at: 99 },
]
// Planned minutes per day (Monday done, today is Tuesday, Sunday is the rest day).
const WEEK = [100, 150, 100, 100, 100, 220, 0]
const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

/**
 * The hero: an example "Today" screen that plays by itself. Tasks get ticked, and the plan bar and
 * readiness score move with them, which is how the real dashboard reacts. Clearly labelled as an example.
 */
export function HeroDemo() {
  const [ref, inView] = useInView<HTMLDivElement>(0.2)
  const step = useSteps(10, 1100, inView, true)
  const done = TASKS.filter((t) => step >= t.at).length
  const doneMinutes = TASKS.filter((t) => step >= t.at).reduce((sum, t) => sum + t.minutes, 0)
  const plan = 74 + done * 3
  const readiness = Math.round((76 * 25 + 68 * 35 + plan * 25 + 50 * 15) / 100)

  return (
    <div ref={ref}>
      <Frame path="/dashboard" className="text-left" bodyClassName="flex">
        <aside className="hidden w-44 shrink-0 border-r border-border p-3 md:block" aria-hidden>
          <div className="mb-4 flex items-center gap-2 px-1 text-sm font-semibold">
            <span className="grid h-5 w-5 place-items-center rounded bg-primary text-[11px] font-bold text-primary-fg">J</span> Jadui
          </div>
          {NAV.map(([Icon, label], i) => (
            <div key={label} className={cn('mb-0.5 flex items-center gap-2 rounded-md px-2 py-1.5 text-xs',
              i === 0 ? 'bg-subtle font-medium text-fg' : 'text-fg-muted')}>
              <Icon className="h-3.5 w-3.5" /> {label}
            </div>
          ))}
        </aside>

        <div className="min-w-0 flex-1 p-4 sm:p-5" role="img" aria-label="Example Today screen: tasks being ticked off and the readiness score rising">
          <div className="flex items-end justify-between" aria-hidden>
            <div>
              <p className="text-xs text-fg-subtle">Tuesday · Week 3 of 12</p>
              <p className="text-lg font-semibold">Today</p>
            </div>
            <span className="rounded bg-subtle px-1.5 py-0.5 text-[11px] text-fg-muted">Example</span>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]" aria-hidden>
            <div className="rounded-lg border border-border">
              <div className="flex items-center justify-between border-b border-border px-3 py-2 text-xs">
                <span className="font-medium">Today&apos;s tasks</span>
                <span className="tabular text-fg-subtle">{done} of {TASKS.length} done</span>
              </div>
              <ul className="divide-y divide-border px-3">
                {TASKS.map((t) => {
                  const ticked = step >= t.at
                  return (
                    <li key={t.title} className="flex items-start gap-2.5 py-2.5">
                      <span className={cn('mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border transition-colors duration-300',
                        ticked ? 'border-primary bg-primary text-primary-fg' : 'border-border-strong')}>
                        <Check className={cn('h-3 w-3 transition-transform duration-300', ticked ? 'scale-100' : 'scale-0')} />
                      </span>
                      <span className="min-w-0">
                        <span className={cn('block truncate text-[13px] transition-colors duration-300', ticked && 'text-fg-subtle line-through')}>{t.title}</span>
                        <span className="block text-[11px] text-fg-subtle">{t.meta}</span>
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>

            <div className="space-y-4">
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs font-medium">Readiness</span>
                  <span className="text-[11px] text-fg-subtle">weighted, 4 parts</span>
                </div>
                <p className="tabular mt-1 text-3xl font-semibold">{readiness}</p>
                <div className="mt-2 space-y-1.5">
                  {[['Resume', 76], ['Interviews', 68], ['Plan', plan], ['Gaps closed', 50]].map(([label, value]) => (
                    <div key={label} className="grid grid-cols-[72px_1fr_24px] items-center gap-2 text-[11px]">
                      <span className="text-fg-muted">{label}</span>
                      <span className="h-1.5 overflow-hidden rounded-full bg-subtle">
                        <span className="block h-full rounded-full bg-primary transition-[width] duration-700" style={{ width: `${value}%` }} />
                      </span>
                      <span className="tabular text-right">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-border p-3">
                <span className="text-xs font-medium">This week</span>
                <div className="mt-2 flex h-16 items-end gap-1.5">
                  {WEEK.map((planned, i) => {
                    const d = i === 0 ? planned : i === 1 ? doneMinutes : 0
                    return (
                      <div key={i} className="flex flex-1 flex-col items-center gap-1">
                        <div className="relative w-full rounded-sm bg-subtle" style={{ height: `${(planned / 220) * 48 + 3}px` }}>
                          <div className="absolute inset-x-0 bottom-0 rounded-sm bg-primary transition-[height] duration-700"
                            style={{ height: `${Math.min(1, d / (planned || 1)) * 100}%` }} />
                        </div>
                        <span className="text-[10px] text-fg-subtle">{DAYS[i]}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Frame>
    </div>
  )
}
