'use client'

import { useState } from 'react'
import { AlertTriangle, Save } from 'lucide-react'

import type { Entry, ResumeProfile } from '@/lib/api/types'
import { useUpdateProfile } from '../hooks'
import { ErrorBox } from './ui'

type EntryKey = 'experience' | 'projects'

const toLines = (entry: Entry) => entry.bullets?.map((b) => b.text).join('\n') ?? ''

/**
 * Human-in-the-loop: the AI extracted sections and bullets; the user confirms or fixes them.
 * One textarea per job/project with one bullet per line keeps editing simple.
 * Saving marks every bullet as user-confirmed (the user is the source of truth).
 */
export default function ProfileEditor({ resumeId, profile }: { resumeId: string; profile: ResumeProfile }) {
  const update = useUpdateProfile(resumeId)
  const [skills, setSkills] = useState((profile.skills ?? []).join(', '))
  const [bullets, setBullets] = useState<Record<EntryKey, string[]>>({
    experience: (profile.experience ?? []).map(toLines),
    projects: (profile.projects ?? []).map(toLines),
  })

  const ungrounded = [...(profile.experience ?? []), ...(profile.projects ?? [])]
    .flatMap((e) => e.bullets ?? []).filter((b) => b.grounded === false).length

  const save = () => {
    const withBullets = (key: EntryKey) =>
      (profile[key] ?? []).map((entry, i) => ({
        ...entry,
        bullets: bullets[key][i].split('\n').map((t) => t.trim()).filter(Boolean)
          .map((text) => ({ id: '', text, grounded: true })),  // the backend assigns IDs
      }))
    update.mutate({
      ...profile,
      skills: skills.split(',').map((s) => s.trim()).filter(Boolean),
      experience: withBullets('experience'),
      projects: withBullets('projects'),
    })
  }

  const section = (key: EntryKey, label: string) =>
    (profile[key] ?? []).length > 0 && (
      <div className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">{label}</h3>
        {(profile[key] ?? []).map((entry, i) => (
          <div key={entry.id} className="space-y-1">
            <p className="text-sm font-medium text-fg">
              {entry.title}{entry.org ? ` · ${entry.org}` : ''}
              {(entry.start || entry.end) && <span className="text-muted"> ({entry.start} – {entry.end})</span>}
            </p>
            <textarea
              className="input-base min-h-24 text-sm"
              value={bullets[key][i]}
              onChange={(e) => setBullets((prev) => ({
                ...prev, [key]: prev[key].map((v, j) => (j === i ? e.target.value : v)),
              }))}
            />
          </div>
        ))}
      </div>
    )

  return (
    <details className="card-base" open={ungrounded > 0}>
      <summary className="cursor-pointer text-lg font-semibold text-fg">
        Check what we extracted {profile.education?.length ? '' : '(no education found)'}
      </summary>
      <div className="mt-4 space-y-5">
        {ungrounded > 0 && (
          <div className="flex gap-2 rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {ungrounded} bullet(s) didn&apos;t match your file word-for-word and are excluded from scoring.
            Fix them below and save to confirm.
          </div>
        )}
        {section('experience', 'Experience')}
        {section('projects', 'Projects')}
        <div className="space-y-1">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Skills (comma-separated)</h3>
          <textarea className="input-base min-h-16 text-sm" value={skills} onChange={(e) => setSkills(e.target.value)} />
        </div>
        <button className="btn-primary text-sm" onClick={save} disabled={update.isPending}>
          <Save className="h-4 w-4" /> {update.isPending ? 'Saving…' : update.isSuccess ? 'Saved' : 'Save corrections'}
        </button>
        {update.error && <ErrorBox error={update.error} />}
      </div>
    </details>
  )
}
