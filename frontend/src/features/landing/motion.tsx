'use client'

/**
 * Small helpers for the landing page's scripted demos.
 * Each demo is a list of "steps" advanced by a timer: no video files, no animation library, and the demos are made
 * of the same kind of markup as the real app, so they stay sharp in both themes and at any size.
 */
import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react'

import { cn } from '@/lib/utils'

/** True when the OS asks for reduced motion; demos then show their final state and never auto-advance. */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => { setReduced(mq.matches) }
    update()
    mq.addEventListener('change', update)
    return () => { mq.removeEventListener('change', update) }
  }, [])
  return reduced
}

/** True while the element is on screen, so off-screen demos don't burn CPU or play unseen. */
export function useInView<T extends Element>(threshold = 0.25): [RefObject<T>, boolean] {
  const ref = useRef<T>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => { setInView(entry.isIntersecting) }, { threshold })
    io.observe(el)
    return () => { io.disconnect() }
  }, [threshold])
  return [ref, inView]
}

/**
 * A step counter for a scripted animation: 0, 1, ... `count`, one step every `ms` while `playing`.
 * With `loop` it starts again after a pause of one step. Reduced motion returns `count` (the end state).
 */
export function useSteps(count: number, ms: number, playing: boolean, loop = false) {
  const reduced = useReducedMotion()
  const [step, setStep] = useState(0)
  useEffect(() => {
    if (reduced || !playing) return
    const id = window.setInterval(() => {
      setStep((s) => (s < count ? s + 1 : loop ? 0 : s))
    }, ms)
    return () => { window.clearInterval(id) }
  }, [count, ms, playing, loop, reduced])
  return reduced ? count : step
}

/** Fades and lifts content in. It keeps its space while hidden, so the layout never jumps. */
export function Reveal({ show, children, className, as: Tag = 'div' }: {
  show: boolean; children: ReactNode; className?: string; as?: 'div' | 'li' | 'span' | 'p'
}) {
  return (
    <Tag aria-hidden={!show || undefined}
      className={cn('transition-all duration-500 ease-out', show ? 'translate-y-0 opacity-100' : 'translate-y-1.5 opacity-0', className)}>
      {children}
    </Tag>
  )
}

/** A browser-like frame around a demo, with the app route it shows. */
export function Frame({ path, children, className, bodyClassName }: {
  path: string; children: ReactNode; className?: string; bodyClassName?: string
}) {
  return (
    <div className={cn('overflow-hidden rounded-xl border border-border bg-surface shadow-pop', className)}>
      <div className="flex items-center gap-3 border-b border-border bg-subtle/70 px-3 py-2" aria-hidden>
        <span className="flex gap-1.5">
          {[0, 1, 2].map((i) => <span key={i} className="h-2.5 w-2.5 rounded-full bg-border-strong/40" />)}
        </span>
        <span className="mx-auto truncate rounded border border-border bg-surface px-3 py-0.5 font-mono text-[11px] text-fg-subtle">
          {path}
        </span>
        <span className="w-[42px]" />
      </div>
      <div className={bodyClassName}>{children}</div>
    </div>
  )
}

/** The small selectable chip used in the questionnaire demo (same look as the real wizard). */
export function Chip({ selected, children }: { selected?: boolean; children: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center rounded-md border px-2.5 py-1 text-xs transition-colors duration-300',
      selected ? 'border-primary bg-primary-soft font-medium text-primary-soft-fg' : 'border-border bg-surface text-fg-muted')}>
      {children}
    </span>
  )
}
