import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Join class names; later Tailwind classes win over earlier conflicting ones. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** "1 h 25 min", "45 min" */
export function formatMinutes(minutes: number) {
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  if (!h) return `${m} min`
  return m ? `${h} h ${m} min` : `${h} h`
}

/** "25 Nov", or "25 Nov 2027" when not this year. */
export function formatDay(iso: string) {
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso)
  const sameYear = d.getFullYear() === new Date().getFullYear()
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', ...(sameYear ? {} : { year: 'numeric' }) })
}

/** "Mon, 25 Nov" */
export function formatWeekday(iso: string) {
  return new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })
}

/** "2 h ago", "3 days ago", "25 Nov" */
export function timeAgo(iso: string) {
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`
  if (seconds < 7 * 86400) return `${Math.floor(seconds / 86400)} days ago`
  return formatDay(iso)
}

/** Local date as YYYY-MM-DD (not UTC, so "today" matches the user's calendar). */
export function isoDate(d = new Date()) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function scoreTone(score: number, max = 100): 'success' | 'warning' | 'danger' {
  const ratio = score / max
  return ratio >= 0.75 ? 'success' : ratio >= 0.55 ? 'warning' : 'danger'
}

/** Static class names (Tailwind can't see classes built at runtime like `text-${tone}`). */
export const TONE_TEXT = { success: 'text-success', warning: 'text-warning', danger: 'text-danger' } as const
