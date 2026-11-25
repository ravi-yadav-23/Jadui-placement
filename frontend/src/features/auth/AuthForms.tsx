'use client'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'

import { Button, Field, Input, Notice } from '@/components/ui'
import { Logo } from '@/components/shell/Logo'
import { supabase } from '@/lib/supabase'
import { useAuth } from './AuthProvider'

export function AuthLayout({ title, subtitle, children, footer }: {
  title: string; subtitle?: string; children: ReactNode; footer?: ReactNode
}) {
  const { configured } = useAuth()
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <Logo className="mb-8" />
      <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-6 shadow-sm">
        <h1 className="text-xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-fg-muted">{subtitle}</p>}
        {!configured && (
          <Notice tone="warning" className="mt-4">
            Sign-in isn&apos;t configured: set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.
          </Notice>
        )}
        <div className="mt-5">{children}</div>
      </div>
      {footer && <p className="mt-6 text-sm text-fg-muted">{footer}</p>}
    </div>
  )
}

function useRedirectIfSignedIn() {
  const { user } = useAuth()
  const router = useRouter()
  const next = useSearchParams().get('next') || '/dashboard'
  useEffect(() => { if (user) router.replace(next.startsWith('/') ? next : '/dashboard') }, [user, router, next])
}

export function LoginForm() {
  useRedirectIfSignedIn()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!supabase) return
    setBusy(true)
    setError('')
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setError(error.message === 'Invalid login credentials' ? 'Wrong email or password.' : error.message)
    setBusy(false)
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Email" htmlFor="email">
        <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      <Field label={<span className="flex justify-between">Password <Link href="/auth/forgot" className="font-normal text-primary hover:underline">Forgot?</Link></span>} htmlFor="password">
        <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </Field>
      {error && <Notice>{error}</Notice>}
      <Button type="submit" className="w-full" loading={busy} disabled={!supabase}>Sign in</Button>
    </form>
  )
}

export function SignupForm() {
  useRedirectIfSignedIn()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!supabase) return
    if (form.password.length < 8) return setError('Use at least 8 characters for your password.')
    setBusy(true)
    setError('')
    const { data, error } = await supabase.auth.signUp({
      email: form.email, password: form.password,
      options: { data: { full_name: form.name.trim() }, emailRedirectTo: `${window.location.origin}/dashboard` },
    })
    if (error) setError(error.message)
    else if (!data.session) setSent(true)   // email confirmation is on: the session starts after the link is clicked
    setBusy(false)
  }

  if (sent) {
    return <Notice tone="primary">Check {form.email} for a confirmation link, then come back and sign in.</Notice>
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Name" htmlFor="name">
        <Input id="name" autoComplete="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </Field>
      <Field label="Email" htmlFor="email">
        <Input id="email" type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </Field>
      <Field label="Password" hint="At least 8 characters" htmlFor="password">
        <Input id="password" type="password" autoComplete="new-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
      </Field>
      {error && <Notice>{error}</Notice>}
      <Button type="submit" className="w-full" loading={busy} disabled={!supabase}>Create account</Button>
    </form>
  )
}

export function ForgotForm() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!supabase) return
    const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/auth/reset` })
    if (error) setError(error.message)
    else setSent(true)
  }
  if (sent) return <Notice tone="primary">If an account exists for {email}, a reset link is on its way.</Notice>
  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Email" htmlFor="email">
        <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      {error && <Notice>{error}</Notice>}
      <Button type="submit" className="w-full" disabled={!supabase}>Send reset link</Button>
    </form>
  )
}

/** Opened from the reset email: Supabase reads the recovery token from the URL and starts a session. */
export function ResetForm() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!supabase) return
    if (password.length < 8) return setError('Use at least 8 characters.')
    const { error } = await supabase.auth.updateUser({ password })
    if (error) setError(error.message)
    else router.replace('/dashboard')
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="New password" hint="At least 8 characters" htmlFor="password">
        <Input id="password" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </Field>
      {error && <Notice>{error}</Notice>}
      <Button type="submit" className="w-full" disabled={!supabase}>Save password</Button>
    </form>
  )
}
