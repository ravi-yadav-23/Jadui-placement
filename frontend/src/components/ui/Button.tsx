import Link from 'next/link'
import { forwardRef, type ButtonHTMLAttributes, type ComponentProps } from 'react'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-primary text-primary-fg hover:bg-primary-hover',
  secondary: 'border border-border bg-surface text-fg hover:bg-subtle',
  ghost: 'text-fg-muted hover:bg-subtle hover:text-fg',
  danger: 'bg-danger text-white hover:bg-danger/90 dark:text-bg',
}
const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-9 px-4 text-sm gap-2',
  lg: 'h-11 px-5 text-base gap-2',
}

export function buttonClass(variant: Variant = 'primary', size: Size = 'md', className?: string) {
  return cn('inline-flex shrink-0 items-center justify-center rounded-md font-medium transition-colors',
    'disabled:pointer-events-none disabled:opacity-50', VARIANTS[variant], SIZES[size], className)
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; loading?: boolean }

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading, className, children, disabled, type = 'button', ...props }, ref,
) {
  return (
    <button ref={ref} type={type} disabled={disabled || loading} className={buttonClass(variant, size, className)} {...props}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  )
})

/** A link that looks like a button. */
export function ButtonLink({ variant = 'primary', size = 'md', className, ...props }:
  ComponentProps<typeof Link> & { variant?: Variant; size?: Size }) {
  return <Link className={buttonClass(variant, size, className)} {...props} />
}
