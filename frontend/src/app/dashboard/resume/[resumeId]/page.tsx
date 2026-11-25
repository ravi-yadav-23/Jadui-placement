'use client'

import Link from 'next/link'
import { ArrowLeft, ExternalLink } from 'lucide-react'

import AnalyzePanel from '@/features/resume/components/AnalyzePanel'
import ParseHealthPanel from '@/features/resume/components/ParseHealthPanel'
import ProfileEditor from '@/features/resume/components/ProfileEditor'
import { ErrorBox, Spinner, StatusBadge } from '@/features/resume/components/ui'
import { useResume, useResumeFileUrl } from '@/features/resume/hooks'

/** One resume version: parse health -> confirm extracted profile -> start an analysis. */
export default function ResumePage({ params }: { params: { resumeId: string } }) {
  const resume = useResume(params.resumeId)
  const ready = resume.data?.status === 'ready'
  const file = useResumeFileUrl(params.resumeId, ready)

  return (
    <div className="space-y-6">
      <Link href="/dashboard/resume" className="flex items-center gap-1 text-sm text-muted hover:text-fg">
        <ArrowLeft className="h-4 w-4" /> All resumes
      </Link>
      {resume.error && <ErrorBox error={resume.error} />}
      {resume.isLoading && <Spinner label="Loading…" />}

      {resume.data && (
        <>
          <header className="flex items-center justify-between gap-3">
            <h1 className="truncate text-2xl font-bold text-fg">{resume.data.title}</h1>
            <div className="flex items-center gap-3">
              {file.data && (
                <a href={file.data.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm text-primary">
                  Original <ExternalLink className="h-3 w-3" />
                </a>
              )}
              <StatusBadge status={resume.data.status} />
            </div>
          </header>

          {!ready && resume.data.status !== 'failed' && <Spinner label="Reading your resume and extracting sections…" />}
          {resume.data.status === 'failed' && <ErrorBox error={new Error(resume.data.error || 'Processing failed.')} />}

          {(resume.data.checks?.length ?? 0) > 0 && (
            <ParseHealthPanel checks={resume.data.checks ?? []} rawText={resume.data.raw_text} />
          )}
          {ready && resume.data.profile && (
            <>
              <ProfileEditor resumeId={resume.data.id} profile={resume.data.profile} />
              <AnalyzePanel resumeId={resume.data.id} />
            </>
          )}
        </>
      )}
    </div>
  )
}
