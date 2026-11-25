'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, type ReactNode } from 'react'
import { ArrowLeft, ArrowRight, Check, Plus, Trash2 } from 'lucide-react'

import { Badge, Button, Card, Checkbox, ChoiceCard, Field, Input, Notice, Progress, Segmented, Select, Spinner } from '@/components/ui'
import type { PlannerProfile, PlanPreview, ProfileSuggestions } from '@/lib/api/types'
import { cn, formatDay, formatMinutes, isoDate } from '@/lib/utils'
import { useCreatePlan, usePlannerProfile, usePreviewPlan } from '../hooks'
import { COMPANIES, LANGUAGES, RATING_LABELS, RATING_SUBJECTS, ROLES, subjectLabel } from '../labels'

type Form = PlannerProfile
const STEPS = ['About you', 'Your target', 'Your time', 'Your skills', 'What we know', 'Preview'] as const

const DEFAULTS: Form = {
  status: 'student', degree: 'btech', year: 3, goal: 'placement', company_types: ['product'], target_role: 'sde',
  target_level: 'entry', weekday_hours: 2, weekend_hours: 4, rest_day: 'none', busy: [], study_time: 'evening',
  language: 'python', language_comfort: 2, ratings: {}, problems_solved: '0', projects: 0, projects_deployed: false,
  include_gaps: [], stack: [],
}

/** The questionnaire. Every question changes the plan (see docs/plans/2026-11-25-task-planner-plan.md §4). */
export function SetupWizard() {
  const router = useRouter()
  const saved = usePlannerProfile()
  const preview = usePreviewPlan()
  const create = useCreatePlan()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<Form | null>(null)

  useEffect(() => {
    if (!saved.data || form) return
    const s = saved.data.suggestions
    setForm(saved.data.profile ?? {
      ...DEFAULTS,
      projects: s.projects ?? 0,
      stack: (s.stack ?? []).slice(0, 10),
      ratings: s.ratings as Form['ratings'],
      include_gaps: s.gaps ?? [],
    })
  }, [saved.data, form])

  if (saved.isLoading || !form) return <Spinner label="Loading your answers…" />
  const set = (patch: Partial<Form>) => setForm({ ...form, ...patch })
  const error = validate(step, form)
  const next = () => {
    if (step === STEPS.length - 2) preview.mutate(form)
    setStep(step + 1)
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <p className="text-sm text-fg-muted">Step {step + 1} of {STEPS.length}</p>
        <h1 className="mt-1 text-2xl">{STEPS[step]}</h1>
        <Progress value={step + 1} max={STEPS.length} className="mt-3" label="Setup progress" />
      </div>

      <Card className="p-5 sm:p-6">
        {step === 0 && <AboutYou form={form} set={set} />}
        {step === 1 && <Target form={form} set={set} />}
        {step === 2 && <Time form={form} set={set} />}
        {step === 3 && <Skills form={form} set={set} />}
        {step === 4 && <Known form={form} set={set} suggestions={saved.data!.suggestions} />}
        {step === 5 && <PreviewStep preview={preview.data} loading={preview.isPending} error={preview.error?.message} />}
      </Card>

      {create.error && <Notice className="mt-4">{create.error.message}</Notice>}
      <div className="mt-5 flex items-center justify-between">
        <Button variant="ghost" onClick={() => (step ? setStep(step - 1) : router.back())}>
          <ArrowLeft className="h-4 w-4" /> {step ? 'Back' : 'Cancel'}
        </Button>
        {step < STEPS.length - 1 ? (
          <div className="flex items-center gap-3">
            {error && <span className="text-xs text-fg-subtle">{error}</span>}
            <Button onClick={next} disabled={Boolean(error)} data-testid="wizard-next">Continue <ArrowRight className="h-4 w-4" /></Button>
          </div>
        ) : (
          <Button onClick={() => create.mutate(form, { onSuccess: () => router.push('/dashboard/planner') })}
            loading={create.isPending} disabled={!preview.data} data-testid="create-plan">
            <Check className="h-4 w-4" /> Create my plan
          </Button>
        )}
      </div>
    </div>
  )
}

function validate(step: number, f: Form): string | null {
  if (step === 0 && f.status === 'student' && (!f.year || !f.goal)) return 'Choose your year and goal'
  if (step === 0 && f.status === 'professional' && (f.experience_years === null || f.experience_years === undefined)) return 'Enter your years of experience'
  if (step === 1 && !f.company_types?.length) return 'Choose at least one company type'
  if (step === 2 && f.weekday_hours * 5 + f.weekend_hours * 2 < 1) return 'Plan at least one hour per week'
  return null
}

type StepProps = { form: Form; set: (patch: Partial<Form>) => void }

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="space-y-2.5 [&+&]:mt-6">
      <div>
        <h2 className="text-sm font-semibold">{title}</h2>
        {hint && <p className="text-xs text-fg-muted">{hint}</p>}
      </div>
      {children}
    </section>
  )
}

function AboutYou({ form, set }: StepProps) {
  return (
    <>
      <Section title="Where are you right now?">
        <div className="grid gap-2 sm:grid-cols-3">
          {([['student', 'College student', 'Still studying'], ['graduate', 'Graduate', 'Looking for a first job'],
            ['professional', 'Working professional', 'Have work experience']] as const).map(([value, title, hint]) => (
            <ChoiceCard key={value} selected={form.status === value} onClick={() => set({ status: value })} title={title} description={hint} />
          ))}
        </div>
      </Section>
      {form.status !== 'professional' && (
        <Section title="Degree" hint="BCA and B.Sc students get extra time on CS fundamentals, which some syllabi skip.">
          <Select value={form.degree ?? 'btech'} onChange={(e) => set({ degree: e.target.value as Form['degree'] })} aria-label="Degree" className="max-w-xs">
            <option value="btech">B.Tech / BE</option><option value="bca">BCA</option><option value="mca">MCA</option>
            <option value="mtech">M.Tech</option><option value="bsc">B.Sc</option><option value="other">Other</option>
          </Select>
        </Section>
      )}
      {form.status === 'student' && (
        <>
          <Section title="Year of study" hint="Earlier years get a longer, lighter plan focused on foundations.">
            <Segmented value={form.year ?? 3} onChange={(year) => set({ year })} label="Year of study"
              options={[1, 2, 3, 4, 5].map((y) => ({ value: y, label: `${y}${['st', 'nd', 'rd', 'th', 'th'][y - 1]} year` }))} />
          </Section>
          <Section title="What are you preparing for?">
            <Segmented value={form.goal ?? 'placement'} onChange={(goal) => set({ goal })} label="Goal"
              options={[{ value: 'internship', label: 'Internship' }, { value: 'placement', label: 'Full-time placement' }]} />
          </Section>
        </>
      )}
      {form.status !== 'professional' && (
        <Section title="Graduation (month and year)" hint="Optional.">
          <Input type="month" className="max-w-xs" value={form.graduation ?? ''} onChange={(e) => set({ graduation: e.target.value || null })} aria-label="Graduation month" />
        </Section>
      )}
      {form.status === 'professional' && (
        <>
          <Section title="Years of experience">
            <Input type="number" min={0} max={15} step={0.5} className="max-w-[120px]" value={form.experience_years ?? ''}
              onChange={(e) => set({ experience_years: e.target.value === '' ? null : Number(e.target.value) })} aria-label="Years of experience" />
          </Section>
          <Section title="Current role and stack" hint="Stack as a comma-separated list, e.g. Java, Spring Boot, MySQL.">
            <div className="grid gap-2 sm:grid-cols-2">
              <Input placeholder="e.g. Backend Engineer" value={form.current_role ?? ''} onChange={(e) => set({ current_role: e.target.value || null })} aria-label="Current role" />
              <Input placeholder="Your stack" value={(form.stack ?? []).join(', ')} aria-label="Stack"
                onChange={(e) => set({ stack: e.target.value.split(',').map((s) => s.trim()).filter(Boolean).slice(0, 20) })} />
            </div>
          </Section>
        </>
      )}
    </>
  )
}

function Target({ form, set }: StepProps) {
  const types = form.company_types ?? []
  const toggle = (c: keyof typeof COMPANIES) => set({ company_types: types.includes(c) ? types.filter((x) => x !== c) : [...types, c] })
  return (
    <>
      <Section title="Target role">
        <div className="grid gap-2 sm:grid-cols-3">
          {(Object.keys(ROLES) as (keyof typeof ROLES)[]).map((r) => (
            <ChoiceCard key={r} selected={form.target_role === r} onClick={() => set({ target_role: r })} title={ROLES[r].label} description={ROLES[r].hint} />
          ))}
        </div>
      </Section>
      {form.status === 'professional' ? (
        <Section title="Level you're preparing for" hint="Decides how much low-level and high-level system design you get.">
          <Segmented value={form.target_level ?? 'entry'} onChange={(target_level) => set({ target_level })} label="Target level" options={[
            { value: 'entry', label: 'Entry (0-1 yr)' }, { value: 'mid', label: 'Mid (1-3 yrs)' }, { value: 'senior', label: 'Senior (3-5 yrs)' }]} />
        </Section>
      ) : <p className="mt-6 text-sm text-fg-muted">Students and graduates prepare for entry-level roles.</p>}
      <Section title="Which companies?" hint="Pick all that apply. Service companies add aptitude; top product companies raise DSA difficulty.">
        <div className="grid gap-2 sm:grid-cols-3">
          {(Object.keys(COMPANIES) as (keyof typeof COMPANIES)[]).map((c) => (
            <ChoiceCard key={c} selected={types.includes(c)} onClick={() => toggle(c)} title={COMPANIES[c].label} description={COMPANIES[c].hint} />
          ))}
        </div>
      </Section>
      <Section title="Target date" hint="Your placement drive or interview date. Leave empty and we'll suggest one from your year.">
        <Input type="date" className="max-w-xs" min={isoDate(new Date(Date.now() + 7 * 864e5))} value={form.target_date ?? ''}
          onChange={(e) => set({ target_date: e.target.value || null })} aria-label="Target date" />
      </Section>
    </>
  )
}

function Time({ form, set }: StepProps) {
  const busy = form.busy ?? []
  const updateBusy = (i: number, patch: Partial<(typeof busy)[number]>) => set({ busy: busy.map((b, j) => (j === i ? { ...b, ...patch } : b)) })
  const week = form.weekday_hours * 5 + form.weekend_hours * 2
  return (
    <>
      <Section title="Hours you can study" hint="Be honest: the plan uses 85% of this and adjusts after weekly check-ins.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Each weekday (Mon-Fri)" htmlFor="weekday">
            <Input id="weekday" type="number" min={0} max={8} step={0.5} value={form.weekday_hours} onChange={(e) => set({ weekday_hours: Number(e.target.value) })} />
          </Field>
          <Field label="Each weekend day" hint="Weekends get the long tasks: projects, design, mocks." htmlFor="weekend">
            <Input id="weekend" type="number" min={0} max={10} step={0.5} value={form.weekend_hours} onChange={(e) => set({ weekend_hours: Number(e.target.value) })} />
          </Field>
        </div>
        <p className="text-sm text-fg-muted">That&apos;s <span className="tabular font-medium text-fg">{week} hours</span> a week.</p>
      </Section>
      <Section title="Rest day">
        <Select value={form.rest_day ?? 'none'} onChange={(e) => set({ rest_day: e.target.value as Form['rest_day'] })} className="max-w-xs" aria-label="Rest day">
          <option value="none">No rest day</option>
          {['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map((d) => <option key={d} value={d}>{d[0].toUpperCase() + d.slice(1)}day</option>)}
        </Select>
      </Section>
      <Section title="Busy dates" hint="Exams, travel, festivals: no tasks are planned on these days.">
        <ul className="space-y-2">
          {busy.map((b, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2">
              <Input type="date" className="w-40" value={b.start} onChange={(e) => updateBusy(i, { start: e.target.value })} aria-label="From" />
              <span className="text-fg-subtle">to</span>
              <Input type="date" className="w-40" value={b.end} onChange={(e) => updateBusy(i, { end: e.target.value })} aria-label="To" />
              <Input className="w-36" placeholder="e.g. Mid-sems" value={b.label ?? ''} onChange={(e) => updateBusy(i, { label: e.target.value })} aria-label="Label" />
              <button type="button" onClick={() => set({ busy: busy.filter((_, j) => j !== i) })} className="rounded p-1.5 text-fg-subtle hover:bg-subtle" aria-label="Remove">
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
        <Button variant="secondary" size="sm" onClick={() => set({ busy: [...busy, { start: isoDate(), end: isoDate(), label: '' }] })}>
          <Plus className="h-3.5 w-3.5" /> Add busy dates
        </Button>
      </Section>
      <Section title="When do you usually study?">
        <Segmented value={form.study_time ?? 'evening'} onChange={(study_time) => set({ study_time })} label="Study time" options={[
          { value: 'morning', label: 'Morning' }, { value: 'afternoon', label: 'Afternoon' }, { value: 'evening', label: 'Evening' }, { value: 'night', label: 'Night' }]} />
      </Section>
    </>
  )
}

function Skills({ form, set }: StepProps) {
  const ratings = (form.ratings ?? {}) as Record<string, number>
  return (
    <>
      <Section title="Language for DSA">
        <div className="flex flex-wrap items-center gap-3">
          <Select value={form.language ?? 'python'} onChange={(e) => set({ language: e.target.value as Form['language'] })} className="w-40" aria-label="Language">
            {Object.entries(LANGUAGES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
          <Segmented size="sm" value={form.language_comfort ?? 2} onChange={(language_comfort) => set({ language_comfort })} label="Comfort with the language"
            options={[{ value: 1, label: 'Just started' }, { value: 2, label: 'Basics' }, { value: 3, label: 'Comfortable' }, { value: 4, label: 'Strong' }]} />
        </div>
        <p className="text-xs text-fg-muted">&quot;Just started&quot; or &quot;Basics&quot; adds a short module on using the language for DSA.</p>
      </Section>
      <Section title="How well do you know each subject?" hint="Topics you know well get less time. Mock interview scores can override this.">
        <div className="space-y-2">
          {RATING_SUBJECTS.filter(([key]) => key !== 'aptitude' || form.company_types?.includes('service')).map(([key, label]) => (
            <div key={key} className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm">{label}</span>
              <Segmented size="sm" value={ratings[key] ?? 0} label={label}
                onChange={(v) => set({ ratings: { ...ratings, [key]: v } as Form['ratings'] })}
                options={RATING_LABELS.map((l, i) => ({ value: i, label: l }))} />
            </div>
          ))}
        </div>
      </Section>
      <Section title="Coding problems solved so far (any site)">
        <Segmented value={form.problems_solved ?? '0'} onChange={(problems_solved) => set({ problems_solved })} label="Problems solved" options={[
          { value: '0', label: 'None' }, { value: 'lt50', label: 'Under 50' }, { value: '50_150', label: '50-150' }, { value: '150_300', label: '150-300' }, { value: '300_plus', label: '300+' }]} />
      </Section>
      <Section title="Projects you've built">
        <div className="flex flex-wrap items-center gap-4">
          <Segmented value={form.projects ?? 0} onChange={(projects) => set({ projects })} label="Projects"
            options={[0, 1, 2, 3].map((n) => ({ value: n, label: n === 3 ? '3+' : String(n) }))} />
          <Checkbox checked={Boolean(form.projects_deployed)} onChange={(projects_deployed) => set({ projects_deployed })} label="At least one is deployed / used by people" />
        </div>
      </Section>
    </>
  )
}

function Known({ form, set, suggestions: raw }: StepProps & { suggestions: ProfileSuggestions }) {
  const suggestions = { ...raw, gaps: raw.gaps ?? [], stack: raw.stack ?? [], interview_topics: raw.interview_topics ?? {} }
  const gaps = form.include_gaps ?? []
  const nothing = !suggestions.resume_title && !suggestions.gaps.length && !Object.keys(suggestions.interview_topics).length
  return (
    <>
      {nothing && <p className="text-sm text-fg-muted">Nothing yet. Once you upload a resume or take a mock interview, your gaps and scores show up here and shape the plan. You can continue.</p>}
      {suggestions.resume_title && (
        <Section title="From your resume" hint={suggestions.resume_title}>
          <p className="text-sm text-fg-muted">{suggestions.projects ?? 0} project(s) found{suggestions.stack.length ? `; skills: ${suggestions.stack.join(', ')}` : ''}.</p>
        </Section>
      )}
      {Object.keys(suggestions.interview_topics).length > 0 && (
        <Section title="From your mock interviews" hint="Weak topics get more time even if you rated them high.">
          <div className="flex flex-wrap gap-2">
            {Object.entries(suggestions.interview_topics).map(([t, s]) => <Badge key={t} tone={s >= 75 ? 'success' : s >= 60 ? 'warning' : 'danger'}>{subjectLabel(t)} {s}</Badge>)}
          </div>
        </Section>
      )}
      {suggestions.gaps.length > 0 && (
        <Section title="Skill gaps to include" hint="Matching topics get higher priority; others become small topics of their own.">
          <div className="space-y-2">
            {suggestions.gaps.map((g) => (
              <Checkbox key={g} label={g} checked={gaps.includes(g)} onChange={(on) => set({ include_gaps: on ? [...gaps, g] : gaps.filter((x) => x !== g) })} />
            ))}
          </div>
        </Section>
      )}
    </>
  )
}

function PreviewStep({ preview, loading, error }: { preview?: PlanPreview; loading: boolean; error?: string }) {
  if (loading) return <Spinner label="Building your plan…" />
  if (error) return <Notice>{error}</Notice>
  if (!preview) return null
  const f = { ...preview.feasibility, cut: preview.feasibility.cut ?? [] }
  const total = preview.allocation.reduce((s, a) => s + a.planned_minutes, 0) || 1
  return (
    <div className="space-y-5" data-testid="plan-preview">
      <div className="grid grid-cols-3 gap-4">
        <div><p className="text-xs text-fg-muted">Until</p><p className="mt-0.5 font-semibold">{formatDay(preview.target_date)}</p></div>
        <div><p className="text-xs text-fg-muted">Weeks</p><p className="tabular mt-0.5 font-semibold">{Math.round(preview.weeks)}</p></div>
        <div><p className="text-xs text-fg-muted">Usable hours / week</p><p className="tabular mt-0.5 font-semibold">{preview.hours_per_week}</p></div>
      </div>
      {f.fits ? (
        <Notice tone="primary">Everything fits. Spare time goes to extra practice and mock interviews.</Notice>
      ) : (
        <Notice tone="warning">
          <p>{f.must_covered ? 'All must-have topics fit, but some others don\'t.' : 'Even the must-have topics don\'t all fit.'}</p>
          {f.cut.length > 0 && <p className="mt-1">Left out: {f.cut.slice(0, 6).join(', ')}{f.cut.length > 6 ? ` and ${f.cut.length - 6} more` : ''}.</p>}
          {f.suggestion && <p className="mt-1">{f.suggestion}</p>}
        </Notice>
      )}
      <div>
        <p className="mb-2 text-sm font-medium">Where your time goes</p>
        <ul className="space-y-2">
          {preview.allocation.filter((a) => a.planned_minutes > 0).sort((a, b) => b.planned_minutes - a.planned_minutes).map((a) => (
            <li key={a.subject} className="grid grid-cols-[120px_1fr_64px] items-center gap-3 text-sm">
              <span>{subjectLabel(a.subject)}</span>
              <div className="h-2 rounded-full bg-subtle"><div className="h-2 rounded-full bg-primary" style={{ width: `${(100 * a.planned_minutes) / total}%` }} /></div>
              <span className="tabular text-right text-xs text-fg-muted">{formatMinutes(a.planned_minutes)}</span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="mb-2 text-sm font-medium">Phases</p>
        <ol className="space-y-1 text-sm">
          {preview.roadmap.phases.map((p) => (
            <li key={p.name} className={cn('flex justify-between gap-3')}><span>{p.name}</span><span className="text-fg-subtle">{formatDay(p.start)} – {formatDay(p.end)}</span></li>
          ))}
        </ol>
      </div>
    </div>
  )
}
