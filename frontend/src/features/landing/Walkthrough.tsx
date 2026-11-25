'use client'

import { useEffect, useRef, useState, type ComponentType } from 'react'
import { Pause, Play } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Frame, useInView, useReducedMotion } from './motion'
import { AdaptScene, ProfileScene, ScheduleScene, type SceneProps } from './scenes/plan'
import { CoachScene, InterviewScene, ResumeScene } from './scenes/practice'

type Chapter = { title: string; body: string; path: string; seconds: number; Scene: ComponentType<SceneProps> }

const CHAPTERS: Chapter[] = [
  { title: 'Tell it about your week', path: '/dashboard/planner/setup', seconds: 8.5, Scene: ProfileScene,
    body: 'Five short steps: level, role, company type, language, and the hours you really have. Students are asked their year; working engineers their experience.' },
  { title: 'Get a plan that fits', path: '/dashboard/planner', seconds: 8.5, Scene: ScheduleScene,
    body: 'A scheduler, not a chatbot, places every task. Subjects interleave, prerequisites come first, finished topics come back for review, and no day is overfilled.' },
  { title: 'Practise interviews', path: '/dashboard/interview', seconds: 10.5, Scene: InterviewScene,
    body: 'Rounds on your projects, a job description, OS / DBMS / CN / OOP, or HR. A key point counts only when the feedback can quote your words.' },
  { title: 'Fix your resume honestly', path: '/dashboard/resume', seconds: 9.5, Scene: ResumeScene,
    body: 'See what a parser reads, then get rewrites that may rephrase but never add numbers, tools or claims you didn’t write.' },
  { title: 'Ask the coach', path: '/dashboard/coach', seconds: 8.5, Scene: CoachScene,
    body: 'It answers from your plan, scores and gaps, and suggests actions as buttons. Nothing changes until you click.' },
  { title: 'It adapts when life happens', path: '/dashboard/planner', seconds: 8.5, Scene: AdaptScene,
    body: 'Missed tasks come back, weekly check-ins scale the plan to what you actually finish, and interview scores add or close topics.' },
]

/**
 * "How it works": a chapter list next to a stage that plays a scripted demo of each step.
 * It auto-advances while on screen, pauses on hover or with the pause button (WCAG 2.2.2), and with reduced motion
 * shows each chapter's final state and waits for a click.
 */
export function Walkthrough() {
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)
  const [hovered, setHovered] = useState(false)
  const [ref, inView] = useInView<HTMLDivElement>(0.35)
  const reduced = useReducedMotion()
  const playing = inView && !paused && !hovered && !reduced
  const chapter = CHAPTERS[active]
  const next = () => { setActive((a) => (a + 1) % CHAPTERS.length) }

  // On narrow screens the chapters are a horizontal strip: keep the active one visible (horizontal scroll only).
  const listRef = useRef<HTMLOListElement>(null)
  useEffect(() => {
    const list = listRef.current
    const item = list?.children[active] as HTMLElement | undefined
    if (list && item && list.scrollWidth > list.clientWidth) list.scrollTo({ left: item.offsetLeft - 16, behavior: 'smooth' })
  }, [active])

  return (
    <div ref={ref} className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)] lg:gap-10">
      <div className="min-w-0">
        <ol ref={listRef} className="relative flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:gap-1 lg:overflow-visible" role="tablist" aria-label="How it works">
          {CHAPTERS.map((c, i) => {
            const isActive = i === active
            return (
              <li key={c.title} className="shrink-0 lg:shrink">
                <button type="button" role="tab" aria-selected={isActive} aria-controls="walkthrough-stage"
                  onClick={() => { setActive(i) }}
                  className={cn('relative w-full overflow-hidden rounded-lg border px-4 py-3 text-left transition-colors',
                    isActive ? 'border-border bg-surface shadow-xs' : 'border-transparent hover:bg-subtle')}>
                  <span className="flex items-center gap-3">
                    <span className={cn('tabular text-xs font-medium', isActive ? 'text-primary' : 'text-fg-subtle')}>0{i + 1}</span>
                    <span className={cn('whitespace-nowrap text-sm font-medium lg:whitespace-normal', !isActive && 'text-fg-muted')}>{c.title}</span>
                  </span>
                  <span className={cn('hidden pl-7 text-sm text-fg-muted', isActive && 'lg:mt-1.5 lg:block')}>{c.body}</span>
                  {isActive && !reduced && (
                    <span key={`${active}`} onAnimationEnd={next}
                      className="absolute inset-x-0 bottom-0 h-0.5 origin-left animate-fill bg-primary"
                      style={{ animationDuration: `${c.seconds}s`, animationPlayState: playing ? 'running' : 'paused' }} />
                  )}
                </button>
              </li>
            )
          })}
        </ol>
        <p className="mt-3 text-sm text-fg-muted lg:hidden">{chapter.body}</p>
      </div>

      <div id="walkthrough-stage" role="tabpanel" aria-label={chapter.title} className="min-w-0"
        onMouseEnter={() => { setHovered(true) }} onMouseLeave={() => { setHovered(false) }}>
        <Frame path={chapter.path} bodyClassName="min-h-[440px] p-4 sm:p-6">
          <chapter.Scene key={active} playing={playing || reduced} />
        </Frame>
        <div className="mt-3 flex items-center justify-between text-xs text-fg-subtle">
          <span>Example data. Your own plan uses your answers.</span>
          {!reduced && (
            <button type="button" onClick={() => { setPaused(!paused) }}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 hover:bg-subtle hover:text-fg">
              {paused ? <Play className="h-3.5 w-3.5" aria-hidden /> : <Pause className="h-3.5 w-3.5" aria-hidden />}
              {paused ? 'Play' : 'Pause'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
