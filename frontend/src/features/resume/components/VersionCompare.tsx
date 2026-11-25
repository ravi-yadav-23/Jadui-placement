'use client'

import { useState } from 'react'

import type { AnalysisDetail } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { useAnalyses, useAnalysis, useResumes } from '../hooks'
import { formatDate } from './ui'

/** Pick an earlier analysis of the same kind (same JD for JD matches) and see what changed. */
export default function VersionCompare({ current }: { current: AnalysisDetail }) {
  const analyses = useAnalyses()
  const resumes = useResumes()
  const [otherId, setOtherId] = useState('')
  const other = useAnalysis(otherId)

  const titles = Object.fromEntries((resumes.data ?? []).map((r) => [r.id, r.title]))
  const candidates = (analyses.data ?? []).filter((a) =>
    a.id !== current.id && a.status === 'done' && a.mode === current.mode
    && (current.mode === 'general' || a.jd_id === current.jd_id))

  if (candidates.length === 0) return null

  const before = Object.fromEntries((otherId ? other.data?.sub_scores ?? [] : []).map((s) => [s.key, s.score]))

  return (
    <section className="card-base space-y-3" data-testid="version-compare">
      <h2 className="text-lg font-semibold text-fg">Compare with another version</h2>
      <select className="input-base" value={otherId} onChange={(e) => setOtherId(e.target.value)}>
        <option value="">Choose an earlier analysis…</option>
        {candidates.map((a) => (
          <option key={a.id} value={a.id}>
            {titles[a.resume_id] ?? 'resume'} · {formatDate(a.created_at)} · {a.overall_score}
          </option>
        ))}
      </select>

      {otherId && other.data?.sub_scores && (
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-muted">
            <tr><th className="py-1">Part</th><th>Other</th><th>This</th><th>Change</th></tr>
          </thead>
          <tbody>
            {[...(current.sub_scores ?? []), { key: 'overall', label: 'Overall', score: current.overall_score ?? 0, max: 100 }]
              .map((s) => {
                const was = s.key === 'overall' ? other.data?.overall_score ?? 0 : before[s.key] ?? 0
                const delta = Math.round((s.score - was) * 10) / 10
                return (
                  <tr key={s.key} className={cn('border-t border-border', s.key === 'overall' ? 'font-semibold' : '')}>
                    <td className="py-1 text-fg">{s.label}</td>
                    <td className="text-muted">{was}</td>
                    <td className="text-fg">{s.score}</td>
                    <td className={delta > 0 ? 'text-success' : delta < 0 ? 'text-error' : 'text-muted'}>
                      {delta > 0 ? `+${delta}` : delta}
                    </td>
                  </tr>
                )
              })}
          </tbody>
        </table>
      )}
    </section>
  )
}
