'use client'

import Link from 'next/link'
import { FileText, Trash2 } from 'lucide-react'

import { useAnalyses, useDeleteResume, useResumes } from '@/features/resume/hooks'
import UploadDropzone from '@/features/resume/components/UploadDropzone'
import { ErrorBox, Spinner, StatusBadge, formatDate, scoreColor } from '@/features/resume/components/ui'
import { cn } from '@/lib/utils'

/** Resume library: upload a version, open a version, see recent analyses. */
export default function ResumeLibraryPage() {
  const resumes = useResumes()
  const analyses = useAnalyses()
  const remove = useDeleteResume()
  const titles = Object.fromEntries((resumes.data ?? []).map((r) => [r.id, r.title]))

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
          <FileText className="h-6 w-6 text-primary" /> Resume Screener
        </h1>
        <p className="mt-1 text-sm text-muted">
          Check how parsers read your resume, get bullet-by-bullet feedback, and match it against real job descriptions.
        </p>
      </header>

      <UploadDropzone />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Your resumes</h2>
        {resumes.isLoading && <Spinner label="Loading…" />}
        {resumes.error && <ErrorBox error={resumes.error} />}
        {resumes.data?.length === 0 && <p className="text-sm text-muted">No resumes yet. Upload one above.</p>}
        <ul className="grid gap-3 sm:grid-cols-2">
          {resumes.data?.map((resume) => (
            <li key={resume.id} className="card-base flex items-start justify-between gap-3 p-4">
              <Link href={`/dashboard/resume/${resume.id}`} className="min-w-0 flex-1">
                <p className="truncate font-medium text-white hover:text-primary">{resume.title}</p>
                <p className="mt-1 flex items-center gap-2 text-xs text-muted">
                  {formatDate(resume.created_at)} <StatusBadge status={resume.status} />
                </p>
              </Link>
              <button
                title="Delete resume"
                className="text-muted hover:text-error"
                onClick={() => confirm(`Delete "${resume.title}" and its analyses?`) && remove.mutate(resume.id)}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      </section>

      {(analyses.data?.length ?? 0) > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-white">Recent analyses</h2>
          <ul className="space-y-2">
            {analyses.data?.slice(0, 10).map((a) => (
              <li key={a.id}>
                <Link href={`/dashboard/resume/analysis/${a.id}`}
                  className="card-base flex items-center justify-between p-3 hover:border-primary/50">
                  <span className="text-sm text-white">
                    {a.mode === 'jd' ? 'JD match' : 'General review'} · {titles[a.resume_id] ?? 'resume'}
                    <span className="ml-2 text-xs text-muted">{formatDate(a.created_at)}</span>
                  </span>
                  {a.overall_score != null
                    ? <span className={cn('font-bold', scoreColor(a.overall_score))}>{a.overall_score}</span>
                    : <StatusBadge status={a.status} />}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
