/** Form controls: label + control + hint, styled consistently. */
import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

const control = 'w-full rounded-md border border-border-strong bg-surface text-sm text-fg placeholder:text-fg-subtle ' +
  'focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:opacity-60'

export function Field({ label, hint, error, children, className, htmlFor }: {
  label: ReactNode; hint?: ReactNode; error?: string; children: ReactNode; className?: string; htmlFor?: string
}) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={htmlFor} className="block text-sm font-medium">{label}</label>
      {children}
      {error ? <p className="text-xs text-danger">{error}</p> : hint && <p className="text-xs text-fg-subtle">{hint}</p>}
    </div>
  )
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cn(control, 'h-9 px-3', className)} {...props} />
})

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(control, 'px-3 py-2 leading-relaxed', className)} {...props} />
})

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(control, 'h-9 px-2.5', className)} {...props} />
}

/** A row of mutually exclusive options (radio-group semantics). */
export function Segmented<T extends string | number>({ options, value, onChange, className, size = 'md', label }: {
  options: { value: T; label: ReactNode }[]; value: T; onChange: (value: T) => void; className?: string; size?: 'sm' | 'md'; label?: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className={cn('inline-flex flex-wrap gap-1 rounded-md border border-border bg-subtle p-0.5', className)}>
      {options.map((o) => (
        <button key={String(o.value)} type="button" role="radio" aria-checked={o.value === value} onClick={() => onChange(o.value)}
          className={cn('rounded px-3 font-medium transition-colors', size === 'sm' ? 'h-7 text-xs' : 'h-8 text-sm',
            o.value === value ? 'bg-surface text-fg shadow-xs' : 'text-fg-muted hover:text-fg')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Selectable cards (single or multi choice). */
export function ChoiceCard({ selected, onClick, title, description, className }: {
  selected: boolean; onClick: () => void; title: ReactNode; description?: ReactNode; className?: string
}) {
  return (
    <button type="button" onClick={onClick} aria-pressed={selected}
      className={cn('rounded-md border px-3.5 py-3 text-left transition-colors',
        selected ? 'border-primary bg-primary-soft' : 'border-border bg-surface hover:border-border-strong', className)}>
      <span className={cn('block text-sm font-medium', selected && 'text-primary-soft-fg')}>{title}</span>
      {description && <span className="mt-0.5 block text-xs text-fg-muted">{description}</span>}
    </button>
  )
}

export function Checkbox({ checked, onChange, label, className, disabled }: {
  checked: boolean; onChange: (checked: boolean) => void; label: ReactNode; className?: string; disabled?: boolean
}) {
  return (
    <label className={cn('flex cursor-pointer items-start gap-2.5 text-sm', disabled && 'cursor-default opacity-60', className)}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-border-strong accent-[rgb(var(--primary))]" />
      <span>{label}</span>
    </label>
  )
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { value: T; label: ReactNode }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div role="tablist" className="flex gap-5 border-b border-border">
      {tabs.map((t) => (
        <button key={t.value} role="tab" type="button" aria-selected={t.value === value} onClick={() => onChange(t.value)}
          className={cn('-mb-px border-b-2 pb-2.5 text-sm font-medium transition-colors',
            t.value === value ? 'border-primary text-fg' : 'border-transparent text-fg-muted hover:text-fg')}>
          {t.label}
        </button>
      ))}
    </div>
  )
}
