'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Play } from 'lucide-react'

import type { CreateInterview } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { ErrorBox } from '@/features/resume/components/ui'
import { useJds, useResumes } from '@/features/resume/hooks'
import { useCreateInterview } from '../hooks'
import { TOPICS, TRACKS, type TopicKey, type TrackKey } from '../labels'

/** Setup form: track, questions, mode, and the resume / JD the questions come from. */
export default function TrackPicker() {
  const router = useRouter()
  const create = useCreateInterview()
  const resumes = (useResumes().data ?? []).filter((r) => r.status === 'ready')
  const jds = (useJds().data ?? []).filter((j) => j.status === 'ready')

  const [track, setTrack] = useState<TrackKey>('mixed')
  const [topics, setTopics] = useState<TopicKey[]>(['os', 'dbms', 'cn', 'oop'])
  const [difficulty, setDifficulty] = useState<CreateInterview['difficulty']>('any')
  const [count, setCount] = useState(5)
  const [mode, setMode] = useState<'interview' | 'practice'>('interview')
  const [resumeId, setResumeId] = useState('')
  const [jdId, setJdId] = useState('')
  const [role, setRole] = useState('')

  const usesTopics = track === 'fundamentals' || track === 'mixed'
  const usesResume = track === 'resume' || track === 'mixed' || track === 'jd'
  const missing = (track === 'resume' && !resumeId) || (track === 'jd' && !jdId) || (usesTopics && topics.length === 0)

  const toggleTopic = (t: TopicKey) =>
    setTopics((current) => (current.includes(t) ? current.filter((x) => x !== t) : [...current, t]))

  const start = () => create.mutate({
    track, mode, question_count: count, topics, difficulty,
    resume_id: usesResume && resumeId ? resumeId : null,
    jd_id: track === 'jd' ? jdId : null,
    target_role: role.trim() || null,
  }, { onSuccess: (data) => router.push(`/dashboard/interview/${data.id}`) })

  return (
    <section className="card-base space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(Object.keys(TRACKS) as TrackKey[]).map((key) => (
          <button key={key} onClick={() => setTrack(key)} data-testid={`track-${key}`}
            className={cn('rounded-xl border p-4 text-left transition',
              track === key ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/50')}>
            <p className="font-semibold text-white">{TRACKS[key].label}</p>
            <p className="mt-1 text-xs text-muted">{TRACKS[key].hint}</p>
          </button>
        ))}
      </div>

      {usesTopics && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted">Topics:</span>
          {(Object.keys(TOPICS) as TopicKey[]).map((t) => (
            <button key={t} onClick={() => toggleTopic(t)}
              className={cn('rounded-full border px-3 py-1', topics.includes(t) ? 'border-primary text-primary' : 'border-border text-muted')}>
              {TOPICS[t]}
            </button>
          ))}
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as CreateInterview['difficulty'])}
            className="input-base ml-auto w-auto">
            <option value="any">Any difficulty</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {usesResume && (
          <label className="text-sm text-muted">
            Resume {track === 'resume' ? '(required)' : '(optional)'}
            <select value={resumeId} onChange={(e) => setResumeId(e.target.value)} className="input-base mt-1">
              <option value="">{resumes.length ? 'None' : 'No parsed resume yet'}</option>
              {resumes.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
            </select>
          </label>
        )}
        {track === 'jd' && (
          <label className="text-sm text-muted">
            Job description (required)
            <select value={jdId} onChange={(e) => setJdId(e.target.value)} className="input-base mt-1">
              <option value="">{jds.length ? 'Choose a JD' : 'Save a JD in the resume screener first'}</option>
              {jds.map((j) => <option key={j.id} value={j.id}>{j.title}{j.company ? ` · ${j.company}` : ''}</option>)}
            </select>
          </label>
        )}
        <label className="text-sm text-muted">
          Target role (optional)
          <input value={role} onChange={(e) => setRole(e.target.value)} maxLength={120}
            placeholder="e.g. Backend SDE intern" className="input-base mt-1" />
        </label>
        <label className="text-sm text-muted">
          Questions: <b className="text-white">{count}</b> <span className="text-xs">(+ up to one follow-up each)</span>
          <input type="range" min={3} max={8} value={count} onChange={(e) => setCount(Number(e.target.value))}
            className="mt-2 w-full accent-primary" />
        </label>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-lg border border-border p-1 text-sm">
          {(['interview', 'practice'] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={cn('rounded-md px-3 py-1', mode === m ? 'bg-primary text-white' : 'text-muted')}>
              {m === 'interview' ? 'Interview mode' : 'Practice mode'}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted">
          {mode === 'interview' ? 'Feedback at the end, like a real interview.' : 'Feedback after every answer.'}
        </p>
        <button onClick={start} disabled={missing || create.isPending} data-testid="start-interview"
          className="btn-primary flex items-center gap-2 disabled:opacity-50">
          <Play className="h-4 w-4" /> {create.isPending ? 'Starting…' : 'Start interview'}
        </button>
      </div>
      {create.error && <ErrorBox error={create.error} />}
    </section>
  )
}
