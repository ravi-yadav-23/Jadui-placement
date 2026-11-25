'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Briefcase, FileSearch, Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'
import { useCreateAnalysis, useCreateJd, useJd, useJds } from '../hooks'
import { ErrorBox, StatusBadge } from './ui'

/** Start a general review, or match against a saved / newly pasted job description. */
export default function AnalyzePanel({ resumeId }: { resumeId: string }) {
  const router = useRouter()
  const [mode, setMode] = useState<'general' | 'jd'>('general')
  const [targetRole, setTargetRole] = useState('')
  const [jdText, setJdText] = useState('')
  const [jdId, setJdId] = useState<string | null>(null)

  const jds = useJds()
  const createJd = useCreateJd()
  const selectedJd = useJd(jdId)       // polls while the JD is being parsed
  const createAnalysis = useCreateAnalysis()

  const start = () =>
    createAnalysis.mutate(
      mode === 'general'
        ? { resume_id: resumeId, mode, target_role: targetRole.trim() || null }
        : { resume_id: resumeId, mode, jd_id: jdId },
      { onSuccess: (analysis) => router.push(`/dashboard/resume/analysis/${analysis.id}`) },
    )

  const saveJd = () =>
    createJd.mutate({ raw_text: jdText.trim() }, { onSuccess: (jd) => { setJdId(jd.id); setJdText('') } })

  const jdReady = selectedJd.data?.status === 'ready'
  const tab = (value: 'general' | 'jd', label: string, Icon: typeof Briefcase) => (
    <button
      onClick={() => setMode(value)}
      className={cn('flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium',
        mode === value ? 'bg-primary text-primary-fg' : 'text-muted hover:text-fg')}
    >
      <Icon className="h-4 w-4" /> {label}
    </button>
  )

  return (
    <section className="card-base space-y-4">
      <div className="flex w-fit gap-1 rounded-lg border border-border bg-surface p-1">
        {tab('general', 'General review', FileSearch)}
        {tab('jd', 'Match a job', Briefcase)}
      </div>

      {mode === 'general' ? (
        <input className="input-base" placeholder="Target role (optional), e.g. Backend Engineer"
          value={targetRole} onChange={(e) => setTargetRole(e.target.value)} />
      ) : (
        <div className="space-y-3">
          {(jds.data?.length ?? 0) > 0 && (
            <select className="input-base" value={jdId ?? ''} onChange={(e) => setJdId(e.target.value || null)}>
              <option value="">Choose a saved job description…</option>
              {jds.data?.map((jd) => (
                <option key={jd.id} value={jd.id}>{jd.title || 'Untitled'}{jd.company ? ` · ${jd.company}` : ''}</option>
              ))}
            </select>
          )}
          <textarea className="input-base min-h-40 text-sm" placeholder="…or paste a new job description here"
            value={jdText} onChange={(e) => setJdText(e.target.value)} data-testid="jd-input" />
          {jdText.trim().length > 0 && (
            <button className="btn-outline text-sm" onClick={saveJd} disabled={createJd.isPending || jdText.trim().length < 100}>
              {createJd.isPending ? 'Saving…' : jdText.trim().length < 100 ? 'Paste the full JD (100+ characters)' : 'Save job description'}
            </button>
          )}
          {selectedJd.data && (
            <p className="flex items-center gap-2 text-sm text-muted">
              Selected: {selectedJd.data.title || 'job description'} <StatusBadge status={selectedJd.data.status} />
              {selectedJd.data.error && <span className="text-error">{selectedJd.data.error}</span>}
            </p>
          )}
          {createJd.error && <ErrorBox error={createJd.error} />}
        </div>
      )}

      <button className="btn-primary w-full justify-center" onClick={start} data-testid="run-analysis"
        disabled={createAnalysis.isPending || (mode === 'jd' && !jdReady)}>
        {createAnalysis.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        {mode === 'general' ? 'Review my resume' : jdReady ? 'Match against this job' : 'Choose or save a job first'}
      </button>
      {createAnalysis.error && <ErrorBox error={createAnalysis.error} />}
    </section>
  )
}
