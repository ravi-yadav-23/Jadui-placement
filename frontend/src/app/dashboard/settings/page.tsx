'use client'

import { useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

import { Button, ButtonLink, Card, CardHeader, Dialog, Field, Input, Notice, PageHeader, Segmented } from '@/components/ui'
import { useAuth } from '@/features/auth/AuthProvider'
import { useTheme, type Theme } from '@/features/auth/theme'
import { usePlannerProfile } from '@/features/planner/hooks'
import { COMPANIES, LANGUAGES, ROLES } from '@/features/planner/labels'
import { api } from '@/lib/api/client'

export default function SettingsPage() {
  const { user, signOut } = useAuth()
  const { theme, setTheme } = useTheme()
  const profile = usePlannerProfile()
  const router = useRouter()
  const answers = profile.data?.profile

  return (
    <>
      <PageHeader title="Settings" />
      <div className="space-y-6">
        <Card>
          <CardHeader title="Account" />
          <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
            <div>
              <p className="font-medium">{user?.name}</p>
              <p className="text-sm text-fg-muted">{user?.email}</p>
            </div>
            <Button variant="secondary" onClick={async () => { await signOut(); router.replace('/auth/login') }}>Sign out</Button>
          </div>
        </Card>

        <Card>
          <CardHeader title="Appearance" />
          <div className="px-5 py-4">
            <Segmented<Theme> value={theme} onChange={setTheme} label="Theme" options={[
              { value: 'light', label: 'Light' }, { value: 'system', label: 'System' }, { value: 'dark', label: 'Dark' }]} />
          </div>
        </Card>

        <Card>
          <CardHeader title="Study profile" description="Your planner answers. Changing them builds a new plan; finished work is kept in the old one."
            action={<ButtonLink href="/dashboard/planner/setup" variant="secondary" size="sm">{answers ? 'Edit' : 'Set up'}</ButtonLink>} />
          {answers ? (
            <dl className="grid gap-x-6 gap-y-3 px-5 py-4 text-sm sm:grid-cols-2">
              <Item label="Status" value={answers.status === 'student' ? `Student, year ${answers.year}` : answers.status === 'professional' ? `Professional, ${answers.experience_years} yrs` : 'Graduate'} />
              <Item label="Target role" value={ROLES[answers.target_role ?? 'sde'].label} />
              <Item label="Companies" value={(answers.company_types ?? []).map((c) => COMPANIES[c].label).join(', ')} />
              <Item label="Time" value={`${answers.weekday_hours} h weekdays, ${answers.weekend_hours} h weekend days`} />
              <Item label="Language" value={LANGUAGES[answers.language ?? 'python']} />
              <Item label="Target date" value={answers.target_date ?? 'Suggested from your year'} />
            </dl>
          ) : <p className="px-5 py-4 text-sm text-fg-muted">Not set up yet.</p>}
        </Card>

        <DangerZone />
      </div>
    </>
  )
}

function Item({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs text-fg-subtle">{label}</dt><dd className="mt-0.5">{value}</dd></div>
}

function DangerZone() {
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const client = useQueryClient()
  const router = useRouter()
  const remove = async () => {
    setBusy(true)
    try {
      await api<void>('/me/data', { method: 'DELETE' })
      client.clear()
      router.replace('/dashboard')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not delete your data.')
      setBusy(false)
    }
  }
  return (
    <Card className="border-danger/30">
      <CardHeader title="Delete my data" description="Removes your resumes and files, job descriptions, analyses, interviews, plans and coach messages. Your sign-in account stays." />
      <div className="px-5 py-4"><Button variant="danger" onClick={() => setOpen(true)}>Delete all my data</Button></div>
      <Dialog open={open} onClose={() => setOpen(false)} title="Delete all your data?" description="This can't be undone."
        footer={<>
          <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="danger" disabled={typed !== 'DELETE'} loading={busy} onClick={remove}>Delete everything</Button>
        </>}>
        <Field label={<>Type <span className="font-mono">DELETE</span> to confirm</>} htmlFor="confirm-delete">
          <Input id="confirm-delete" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        </Field>
        {error && <Notice className="mt-3">{error}</Notice>}
      </Dialog>
    </Card>
  )
}
