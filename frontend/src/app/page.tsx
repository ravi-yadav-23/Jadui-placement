'use client'

import { ArrowRight, Github } from 'lucide-react'

import { ButtonLink } from '@/components/ui'
import { Logo } from '@/components/shell/Logo'
import { useAuth } from '@/features/auth/AuthProvider'
import { HeroDemo } from '@/features/landing/HeroDemo'
import { Faq, LoopDiagram, PersonaMix } from '@/features/landing/sections'
import { Walkthrough } from '@/features/landing/Walkthrough'

const REPO = 'https://github.com/ravi-yadav-23/Jadui-placement'

// Every number here is a real property of the product (question bank, parser checks, scheduler, eval).
const FACTS = [
  ['52', 'interview questions, each with written key points and a 1–5 scale'],
  ['16', 'checks on how a parser reads your resume'],
  ['2 · 7 · 21', 'days after a topic, it comes back for review'],
  ['8', 'sample students the planner is tested against on every change'],
]

const TRUST = [
  { title: 'The schedule is code', formula: 'next subject = most behind its share',
    body: 'Weighted fair interleaving, like a network scheduler. Property tests check that no day is overfilled and no topic comes before what it needs.' },
  { title: 'Scores you can check', formula: 'score = 0.6 × rubric + 0.4 × key points',
    body: 'A key point counts only when the feedback quotes your own words. A longer answer doesn’t score higher.' },
  { title: 'Rewrites never invent', formula: 'new number or tool in a rewrite → blocked',
    body: 'Suggestions may rephrase your resume but not add facts. Missing metrics become questions for you.' },
  { title: 'The coach can’t act alone', formula: 'actions ⊆ your real tasks and dates',
    body: 'Suggested actions are checked against your data and shown as buttons. Nothing runs until you click.' },
]

export default function LandingPage() {
  const { user } = useAuth()
  const start = user ? '/dashboard' : '/auth/signup'
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-border bg-bg/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
          <Logo />
          <nav className="flex items-center gap-1">
            {[['#how', 'How it works'], ['#plans', 'Who it’s for'], ['#faq', 'FAQ']].map(([href, label]) => (
              <a key={href} href={href} className="hidden rounded-md px-3 py-1.5 text-sm text-fg-muted hover:text-fg md:block">{label}</a>
            ))}
            <a href={REPO} target="_blank" rel="noreferrer" aria-label="Source on GitHub"
              className="hidden rounded-md p-2 text-fg-muted hover:text-fg sm:block"><Github className="h-4 w-4" /></a>
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
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="bg-dots pointer-events-none absolute inset-0" aria-hidden />
          <div className="relative mx-auto max-w-6xl px-5 pb-16 pt-16 sm:pt-24">
            <div className="mx-auto max-w-3xl animate-fade-up text-center">
              <a href="#how" className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-fg-muted shadow-xs hover:text-fg">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" /> For software placements: campus and experienced
              </a>
              <h1 className="mt-6 text-4xl [text-wrap:balance] sm:text-6xl">Placement prep that knows where you stand.</h1>
              <p className="mx-auto mt-5 max-w-2xl text-lg text-fg-muted">
                A study plan built around the hours you really have, mock interviews scored with evidence, an honest
                resume review, and a coach that answers from your own progress.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <ButtonLink href={start} size="lg">{user ? 'Open app' : 'Build my plan'} <ArrowRight className="h-4 w-4" /></ButtonLink>
                <ButtonLink href="#how" variant="secondary" size="lg">See how it works</ButtonLink>
              </div>
              <p className="mt-4 text-sm text-fg-subtle">Free and open source. Five questions, about three minutes.</p>
            </div>
            <div className="mx-auto mt-14 max-w-5xl animate-fade-up [animation-delay:150ms]">
              <HeroDemo />
            </div>
          </div>
        </section>

        {/* Facts */}
        <section className="border-y border-border bg-surface">
          <dl className="mx-auto grid max-w-6xl grid-cols-2 divide-border px-5 lg:grid-cols-4 lg:divide-x">
            {FACTS.map(([value, label]) => (
              <div key={label} className="px-2 py-8 lg:px-6">
                <dt className="sr-only">{label}</dt>
                <dd className="tabular text-2xl font-semibold">{value}</dd>
                <dd className="mt-1 text-sm text-fg-muted">{label}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* How it works */}
        <section id="how" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 sm:py-24">
          <SectionTitle eyebrow="How it works" title="From five questions to a plan that keeps up with you"
            body="Watch each part work with example data. It plays by itself; pick a step to jump to it." />
          <div className="mt-12"><Walkthrough /></div>
        </section>

        {/* Personalisation */}
        <section id="plans" className="scroll-mt-20 border-y border-border bg-surface">
          <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 py-20 lg:grid-cols-[1fr_1.2fr] lg:gap-16">
            <SectionTitle eyebrow="Who it’s for" title="Same product, a different plan for each person"
              body="Your level and target companies set the starting mix of subjects. Inside each subject, your self-ratings, interview scores and resume gaps decide which topics get more time." />
            <PersonaMix />
          </div>
        </section>

        {/* The loop */}
        <section className="mx-auto max-w-6xl px-5 py-20 sm:py-24">
          <div className="grid items-center gap-10 lg:grid-cols-[1fr_1.4fr] lg:gap-16">
            <SectionTitle eyebrow="One loop" title="Every part feeds the next"
              body="Most prep tools are separate checklists. Here, what you get wrong in an interview or miss on your resume becomes study time, and the plan schedules the interview that checks it." />
            <LoopDiagram />
          </div>
        </section>

        {/* Trust */}
        <section className="border-y border-border bg-surface">
          <div className="mx-auto max-w-6xl px-5 py-20">
            <SectionTitle eyebrow="Built to be checked" title="AI where it helps, code where it must be right" />
            <div className="mt-10 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2">
              {TRUST.map((t) => (
                <div key={t.title} className="bg-surface p-6">
                  <h3 className="text-md">{t.title}</h3>
                  <p className="mt-3 rounded-md bg-subtle px-3 py-2 font-mono text-xs text-fg">{t.formula}</p>
                  <p className="mt-3 text-sm text-fg-muted">{t.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="mx-auto grid max-w-6xl scroll-mt-20 gap-10 px-5 py-20 lg:grid-cols-[1fr_1.6fr] lg:gap-16">
          <SectionTitle eyebrow="FAQ" title="Questions people ask" />
          <Faq />
        </section>

        {/* CTA */}
        <section className="px-5 pb-20">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 rounded-xl bg-fg px-8 py-10 text-bg sm:flex-row sm:items-center">
            <div>
              <h2 className="text-2xl text-bg">Start with your plan</h2>
              <p className="mt-1 text-bg/70">Five questions, about three minutes. Delete your data any time.</p>
            </div>
            <ButtonLink href={start} size="lg">{user ? 'Open app' : 'Create an account'} <ArrowRight className="h-4 w-4" /></ButtonLink>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-8 text-sm text-fg-subtle">
          <div className="flex items-center gap-4">
            <Logo className="text-sm" />
            <span className="hidden sm:inline">Study plan · Mock interviews · Resume review · Coach</span>
          </div>
          <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 hover:text-fg"><Github className="h-4 w-4" /> Source on GitHub</a>
        </div>
      </footer>
    </div>
  )
}

function SectionTitle({ eyebrow, title, body }: { eyebrow: string; title: string; body?: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-sm font-medium text-primary">{eyebrow}</p>
      <h2 className="mt-2 text-3xl [text-wrap:balance]">{title}</h2>
      {body && <p className="mt-3 text-md text-fg-muted">{body}</p>}
    </div>
  )
}
