'use client'

import Link from 'next/link'
import { ArrowRight, Check, Github } from 'lucide-react'

import { Badge, ButtonLink, Card, Progress } from '@/components/ui'
import { Logo } from '@/components/shell/Logo'
import { useAuth } from '@/features/auth/AuthProvider'

const REPO = 'https://github.com/ravi-yadav-23/Jadui-placement'

const LOOP = [
  ['Resume', 'See exactly what a parser reads, get bullet-by-bullet feedback, and match against real job descriptions.'],
  ['Mock interviews', 'Campus-style rounds: your projects, a JD, CS fundamentals, HR. One follow-up when you miss something.'],
  ['Study plan', 'Your hours, level, role and deadline become a dated plan across DSA, CS subjects, design and projects.'],
  ['Coach', 'Ask what to do next. It answers from your own plan, scores and gaps, and suggests actions you confirm.'],
] as const

const FEATURES = [
  {
    title: 'A plan built around your real week',
    body: 'Tell it your weekday and weekend hours, rest day and exam dates. A scheduler (not a chatbot) places every task so no day is overfilled, prerequisites come first, and finished topics come back for review after 2, 7 and 21 days. If your goal doesn\'t fit your time, it says so and shows what would.',
    points: ['Entry, 1-3 or 3-5 years: the subject mix changes', 'Service vs product companies: aptitude, DSA difficulty', 'Weekly check-in adjusts to what you actually did'],
  },
  {
    title: 'Interview feedback you can check',
    body: 'Every question has the key points a strong answer covers and a written 1-5 scale for each skill. A point only counts when the feedback can quote your own words, and padding an answer doesn\'t raise the score.',
    points: ['Tracks for resume, JD, OS / DBMS / CN / OOP and HR', 'Practice mode shows feedback after each answer', 'Weak topics flow into your study plan'],
  },
  {
    title: 'A resume review that never invents',
    body: 'Layout-aware parsing for two-column PDFs, 16 parse checks, and suggested rewrites that may rephrase but never add numbers, tools or claims you didn\'t write. JD matching quotes the bullet that proves each requirement.',
    points: ['Name and contacts removed before any AI call', 'Every score shows its formula', 'Missing metrics become questions, not fake numbers'],
  },
]

export default function LandingPage() {
  const { user } = useAuth()
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
          <Logo />
          <nav className="flex items-center gap-1">
            <a href="#how" className="hidden rounded-md px-3 py-1.5 text-sm text-fg-muted hover:text-fg sm:block">How it works</a>
            <a href={REPO} target="_blank" rel="noreferrer" className="hidden rounded-md px-3 py-1.5 text-sm text-fg-muted hover:text-fg sm:block">GitHub</a>
            {user ? (
              <ButtonLink href="/dashboard" size="sm">Open app</ButtonLink>
            ) : (
              <>
                <ButtonLink href="/auth/login" variant="ghost" size="sm">Sign in</ButtonLink>
                <ButtonLink href="/auth/signup" size="sm">Get started</ButtonLink>
              </>
            )}
          </nav>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 lg:grid-cols-[1fr_440px] lg:py-24">
          <div>
            <Badge tone="primary">For students preparing for software placements</Badge>
            <h1 className="mt-4 text-4xl sm:text-5xl">Placement prep that knows where you stand.</h1>
            <p className="mt-5 max-w-xl text-lg text-fg-muted">
              A study plan built around your hours, mock interviews scored with evidence, an honest resume review,
              and a coach that answers from your own progress.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href={user ? '/dashboard' : '/auth/signup'} size="lg">{user ? 'Open app' : 'Get started, free'} <ArrowRight className="h-4 w-4" /></ButtonLink>
              <ButtonLink href="#how" variant="secondary" size="lg">How it works</ButtonLink>
            </div>
          </div>
          <PreviewCard />
        </section>

        <section id="how" className="border-y border-border bg-surface">
          <div className="mx-auto max-w-6xl px-5 py-16">
            <h2 className="text-2xl">Four parts, one loop</h2>
            <p className="mt-2 max-w-2xl text-fg-muted">Each part feeds the next: gaps from your resume and interviews become tasks in your plan, and the coach sees all of it.</p>
            <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              {LOOP.map(([title, body], i) => (
                <li key={title}>
                  <span className="tabular text-sm font-medium text-primary">0{i + 1}</span>
                  <h3 className="mt-2 text-lg">{title}</h3>
                  <p className="mt-1.5 text-sm text-fg-muted">{body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto max-w-6xl space-y-16 px-5 py-20">
          {FEATURES.map((f) => (
            <div key={f.title} className="grid gap-8 lg:grid-cols-[1fr_1fr] lg:gap-16">
              <div>
                <h2 className="text-2xl">{f.title}</h2>
                <p className="mt-3 text-fg-muted">{f.body}</p>
              </div>
              <ul className="space-y-3 self-center">
                {f.points.map((p) => (
                  <li key={p} className="flex gap-3 text-md"><Check className="mt-1 h-4 w-4 shrink-0 text-primary" aria-hidden /> {p}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>

        <section className="border-t border-border">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6 px-5 py-14">
            <div>
              <h2 className="text-2xl">Start with your plan</h2>
              <p className="mt-1 text-fg-muted">Five questions, about three minutes. Your data stays in your account and you can delete it any time.</p>
            </div>
            <ButtonLink href={user ? '/dashboard' : '/auth/signup'} size="lg">{user ? 'Open app' : 'Create an account'}</ButtonLink>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-6 text-sm text-fg-subtle">
          <Logo className="text-sm" />
          <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 hover:text-fg"><Github className="h-4 w-4" /> Source on GitHub</a>
        </div>
      </footer>
    </div>
  )
}

/** A static picture of the Today screen, built from the real components (clearly an example). */
function PreviewCard() {
  const tasks: [string, string, boolean][] = [
    ['Sliding window: solve 2 problems in Python', 'DSA · Practice · 1 h', true],
    ['Review: Deadlocks', 'OS · Review · 15 min', true],
    ['Indexing and B+ trees', 'DBMS · Learn · 45 min', false],
  ]
  return (
    <Card className="p-0 shadow-pop" aria-label="Example of the Today screen">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-sm font-semibold">Today</span>
        <Badge>Example</Badge>
      </div>
      <ul className="divide-y divide-border px-4">
        {tasks.map(([title, meta, done]) => (
          <li key={title} className="flex items-start gap-3 py-2.5">
            <span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border ${done ? 'border-primary bg-primary text-primary-fg' : 'border-border-strong'}`}>
              {done && <Check className="h-3 w-3" />}
            </span>
            <span className="min-w-0">
              <span className={`block text-sm ${done ? 'text-fg-subtle line-through' : ''}`}>{title}</span>
              <span className="block text-xs text-fg-subtle">{meta}</span>
            </span>
          </li>
        ))}
      </ul>
      <div className="space-y-3 border-t border-border px-4 py-4">
        {[['Mock interviews', 68], ['Study plan', 82], ['Resume', 74]].map(([label, value]) => (
          <div key={label as string}>
            <div className="flex justify-between text-xs"><span className="text-fg-muted">{label}</span><span className="tabular">{value}</span></div>
            <Progress value={value as number} className="mt-1" label={label as string} />
          </div>
        ))}
      </div>
      <p className="border-t border-border px-4 py-3 text-xs text-fg-subtle">
        <Link href="/auth/signup" className="text-primary hover:underline">Your own plan</Link> uses your hours, deadline and skills.
      </p>
    </Card>
  )
}
