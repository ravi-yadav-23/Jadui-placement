import Link from 'next/link'

import { cn } from '@/lib/utils'

/** Wordmark: a small jade square with "J", then the name. No gradient, no icon library glyph. */
export function Logo({ href = '/', className }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={cn('inline-flex items-center gap-2 font-semibold tracking-tight text-fg', className)}>
      <span className="grid h-6 w-6 place-items-center rounded bg-primary text-[13px] font-bold text-primary-fg">J</span>
      <span>Jadui Placement</span>
    </Link>
  )
}
