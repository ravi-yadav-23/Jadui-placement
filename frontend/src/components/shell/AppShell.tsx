'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState, type ReactNode } from 'react'
import { CalendarCheck, FileText, Home, LogOut, Menu, MessageSquare, Mic, Monitor, Moon, Settings, Sun, X } from 'lucide-react'

import { Segmented, Spinner } from '@/components/ui'
import { useAuth } from '@/features/auth/AuthProvider'
import { useTheme, type Theme } from '@/features/auth/theme'
import { cn } from '@/lib/utils'
import { Logo } from './Logo'

export const NAV = [
  { href: '/dashboard', label: 'Today', icon: Home },
  { href: '/dashboard/planner', label: 'Planner', icon: CalendarCheck },
  { href: '/dashboard/interview', label: 'Interviews', icon: Mic },
  { href: '/dashboard/resume', label: 'Resume', icon: FileText },
  { href: '/dashboard/coach', label: 'Coach', icon: MessageSquare },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

function isActive(pathname: string, href: string) {
  return href === '/dashboard' ? pathname === href : pathname.startsWith(href)
}

/** Signed-in layout: sidebar on desktop, top bar + drawer on mobile. Redirects to sign-in without a session. */
export default function AppShell({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!loading && !user) router.replace(`/auth/login?next=${encodeURIComponent(pathname)}`)
  }, [loading, user, router, pathname])
  useEffect(() => { setOpen(false) }, [pathname])

  if (loading || !user) return <Spinner label="Loading…" className="justify-center py-32" />

  return (
    <div className="min-h-screen md:grid md:grid-cols-[232px_1fr]">
      <aside className="sticky top-0 hidden h-screen flex-col border-r border-border bg-surface md:flex">
        <SidebarContent pathname={pathname} />
      </aside>

      <div className="sticky top-0 z-20 flex h-12 items-center justify-between border-b border-border bg-surface px-4 md:hidden">
        <Logo href="/dashboard" />
        <button onClick={() => setOpen(true)} className="rounded p-1.5 text-fg-muted hover:bg-subtle" aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </button>
      </div>
      {open && (
        <div className="fixed inset-0 z-30 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col border-r border-border bg-surface">
            <button onClick={() => setOpen(false)} className="absolute right-3 top-3 rounded p-1.5 text-fg-muted hover:bg-subtle" aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
            <SidebarContent pathname={pathname} />
          </aside>
        </div>
      )}

      <main className="min-w-0 px-4 py-6 sm:px-8 sm:py-8">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
    </div>
  )
}

function SidebarContent({ pathname }: { pathname: string }) {
  return (
    <>
      <div className="flex h-14 items-center px-4"><Logo href="/dashboard" /></div>
      <nav className="flex-1 space-y-0.5 px-2 py-2" aria-label="Main">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = isActive(pathname, href)
          return (
            <Link key={href} href={href} aria-current={active ? 'page' : undefined}
              className={cn('flex h-8 items-center gap-2.5 rounded-md px-2.5 text-sm font-medium transition-colors',
                active ? 'bg-subtle text-fg' : 'text-fg-muted hover:bg-subtle hover:text-fg')}>
              <Icon className={cn('h-4 w-4', active ? 'text-primary' : 'text-fg-subtle')} aria-hidden />
              {label}
            </Link>
          )
        })}
      </nav>
      <UserMenu />
    </>
  )
}

function UserMenu() {
  const { user, signOut } = useAuth()
  const { theme, setTheme } = useTheme()
  const router = useRouter()
  if (!user) return null
  return (
    <div className="space-y-3 border-t border-border p-3">
      <Segmented<Theme> size="sm" label="Theme" value={theme} onChange={setTheme} className="w-full justify-between" options={[
        { value: 'light', label: <Sun className="h-3.5 w-3.5" aria-label="Light" /> },
        { value: 'system', label: <Monitor className="h-3.5 w-3.5" aria-label="System" /> },
        { value: 'dark', label: <Moon className="h-3.5 w-3.5" aria-label="Dark" /> },
      ]} />
      <div className="flex items-center gap-2.5">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-subtle text-xs font-semibold uppercase text-fg-muted">
          {user.name.slice(0, 1)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{user.name}</p>
          <p className="truncate text-xs text-fg-subtle">{user.email}</p>
        </div>
        <button onClick={async () => { await signOut(); router.replace('/auth/login') }}
          className="rounded p-1.5 text-fg-subtle hover:bg-subtle hover:text-fg" aria-label="Sign out" title="Sign out">
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
