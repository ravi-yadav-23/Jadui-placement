'use client'

import { useEffect, useState } from 'react'
import { ChevronDown } from 'lucide-react'

import { Segmented } from '@/components/ui'
import { cn } from '@/lib/utils'
import { useInView, useReducedMotion } from './motion'

// Starting subject mix per profile, grouped from backend/app/planner/curriculum/weights.yaml
// (CS subjects = OS + DBMS + CN + OOP, Design = LLD + HLD). Keep in sync if the weights change.
const SUBJECTS = ['DSA', 'CS subjects', 'Aptitude', 'System design', 'Projects', 'Interview practice', 'Role skills'] as const
const PERSONAS = [
  { id: 'y2', label: '2nd year', mix: [45, 20, 0, 0, 25, 5, 5],
    note: 'Foundations first. OS and networks wait until they’re in your syllabus, and there’s no aptitude yet.' },
  { id: 'service', label: 'Final year · service', mix: [25, 25, 25, 0, 10, 10, 5],
    note: 'Service companies test aptitude and fundamentals, so they get a quarter of the time each.' },
  { id: 'product', label: 'Final year · product', mix: [40, 25, 0, 5, 15, 10, 5],
    note: 'Product companies lean on DSA; a first look at low-level design and stronger projects.' },
  { id: 'mid', label: '1–3 years', mix: [30, 10, 0, 35, 5, 15, 5],
    note: 'Design rounds appear: low-level design first, then high-level. Company type changes DSA difficulty.' },
  { id: 'senior', label: '3–5 years', mix: [20, 5, 0, 45, 0, 25, 5],
    note: 'High-level design leads, with more mock interviews and less time on basics.' },
] as const

/** "Same product, different plan": the subject mix changes with who you are. */
export function PersonaMix() {
  const [id, setId] = useState<(typeof PERSONAS)[number]['id']>('product')
  const [ref, inView] = useInView<HTMLDivElement>(0.3)
  const [seen, setSeen] = useState(false) // grow the bars once, the first time they come into view
  useEffect(() => { if (inView) setSeen(true) }, [inView])
  const persona = PERSONAS.find((p) => p.id === id)!
  return (
    <div ref={ref} className="rounded-xl border border-border bg-surface p-5 shadow-xs sm:p-7">
      <div className="overflow-x-auto pb-1">
        <Segmented value={id} onChange={(v) => { setId(v as typeof id) }} label="Example profile"
          options={PERSONAS.map((p) => ({ value: p.id, label: p.label }))} />
      </div>
      <dl className="mt-6 space-y-3">
        {SUBJECTS.map((s, i) => {
          const value = persona.mix[i]
          return (
            <div key={s} className={cn('grid grid-cols-[110px_1fr_40px] items-center gap-3 text-sm transition-opacity duration-500 sm:grid-cols-[150px_1fr_44px]',
              value === 0 && 'opacity-40')}>
              <dt className="text-fg-muted">{s}</dt>
              <dd className="h-2.5 overflow-hidden rounded-full bg-subtle">
                <span className="block h-full rounded-full bg-primary transition-[width] duration-700 ease-out"
                  style={{ width: seen ? `${value * 2}%` : '0%' }} />
              </dd>
              <dd className="tabular text-right">{value}%</dd>
            </div>
          )
        })}
      </dl>
      <p className="mt-5 border-t border-border pt-4 text-sm text-fg-muted">{persona.note}</p>
    </div>
  )
}

// Loop diagram geometry (viewBox 640 × 300).
const NODES = [
  { id: 'plan', label: 'Study plan', x: 320, y: 42 },
  { id: 'resume', label: 'Resume', x: 92, y: 250 },
  { id: 'interview', label: 'Mock interviews', x: 548, y: 250 },
]
const EDGES = [
  { d: 'M 120 222 Q 150 80 250 52', label: 'skill gaps', lx: 128, ly: 120 },
  { d: 'M 520 222 Q 480 120 392 60', label: 'weak topics', lx: 432, ly: 150 },
  { d: 'M 392 34 Q 600 30 580 222', label: 'checkpoint mocks', lx: 478, ly: 22 },
  { d: 'M 160 262 L 470 262', label: 'questions on your projects', lx: 315, ly: 284 },
]

/** How the parts feed each other. Dots travel along the arrows (static with reduced motion). */
export function LoopDiagram() {
  const reduced = useReducedMotion()
  return (
    <div>
      <svg viewBox="0 0 640 300" className="hidden w-full sm:block" role="img"
        aria-label="Resume skill gaps and weak interview topics feed the study plan; the plan schedules checkpoint mock interviews; interviews ask about your resume projects; the coach reads all of them.">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgb(var(--primary))" />
          </marker>
        </defs>
        {/* The coach in the middle reads everything (dashed). */}
        {NODES.map((n) => (
          <line key={n.id} x1={320} y1={160} x2={n.x} y2={n.y} stroke="rgb(var(--border-strong))" strokeDasharray="3 5" strokeOpacity="0.6" />
        ))}
        {EDGES.map((e, i) => (
          <g key={e.label}>
            <path id={`edge-${i}`} d={e.d} fill="none" stroke="rgb(var(--primary))" strokeWidth="1.5" markerEnd="url(#arrow)" />
            <text x={e.lx} y={e.ly} textAnchor="middle" fontSize="12" fill="rgb(var(--fg-muted))">{e.label}</text>
            {!reduced && (
              <circle r="3.5" fill="rgb(var(--primary))">
                <animateMotion dur="3.2s" repeatCount="indefinite" begin={`${i * 0.8}s`}>
                  <mpath href={`#edge-${i}`} />
                </animateMotion>
              </circle>
            )}
          </g>
        ))}
        {NODES.map((n) => (
          <g key={n.id}>
            <rect x={n.x - 70} y={n.y - 18} width="140" height="36" rx="8" fill="rgb(var(--surface))" stroke="rgb(var(--border-strong))" />
            <text x={n.x} y={n.y + 5} textAnchor="middle" fontSize="14" fontWeight="600" fill="rgb(var(--fg))">{n.label}</text>
          </g>
        ))}
        <rect x={270} y={142} width="100" height="36" rx="8" fill="rgb(var(--primary))" />
        <text x={320} y={165} textAnchor="middle" fontSize="14" fontWeight="600" fill="rgb(var(--primary-fg))">Coach</text>
        <text x={320} y={196} textAnchor="middle" fontSize="11" fill="rgb(var(--fg-subtle))">reads all of it</text>
      </svg>
      <ul className="space-y-2 text-sm sm:hidden">
        <li><b>Resume</b> → skill gaps → <b>Study plan</b></li>
        <li><b>Mock interviews</b> → weak topics → <b>Study plan</b></li>
        <li><b>Study plan</b> → checkpoint mocks → <b>Mock interviews</b></li>
        <li><b>Resume</b> → questions on your projects → <b>Mock interviews</b></li>
        <li><b>Coach</b> reads all of it</li>
      </ul>
    </div>
  )
}

const FAQ = [
  ['Is it free?', 'Yes. It’s an open-source project; you sign up with an email and everything is available.'],
  ['Does an AI make up my schedule?',
    'No. A deterministic scheduler places every task from your hours, rest day and deadline, and tests check it never overfills a day or breaks a prerequisite. The AI only writes the roadmap explanation and project ideas, and code checks those too.'],
  ['What do you send to the AI?',
    'Only what a feature needs. Your name and contact details are removed from your resume before any AI call, and the coach gets a short summary of your progress, not your whole account.'],
  ['I’m already working. Is it for me?',
    'Yes. Choose 1–3 or 3–5 years of experience: the plan shifts toward low- and high-level design, harder DSA and more mock interviews.'],
  ['What if I fall behind?',
    'Missed tasks are kept as history and placed again. After two weekly check-ins the plan uses your real completion rate, so it stops asking for time you don’t have.'],
  ['Can I delete my data?', 'Yes. Settings → Delete my data removes every row and file in your account.'],
] as const

export function Faq() {
  return (
    <div className="divide-y divide-border rounded-xl border border-border bg-surface">
      {FAQ.map(([q, a]) => (
        <details key={q} className="group px-5 [&_summary::-webkit-details-marker]:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-md font-medium">
            {q}
            <ChevronDown className="h-4 w-4 shrink-0 text-fg-subtle transition-transform group-open:rotate-180" aria-hidden />
          </summary>
          <p className="-mt-1 pb-4 text-fg-muted">{a}</p>
        </details>
      ))}
    </div>
  )
}
