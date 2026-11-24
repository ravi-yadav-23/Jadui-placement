'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

import GeneralReviewView from '@/features/resume/components/GeneralReviewView'
import JdMatchView from '@/features/resume/components/JdMatchView'
import { ErrorBox, Spinner, formatDate } from '@/features/resume/components/ui'
import VersionCompare from '@/features/resume/components/VersionCompare'
import { useAnalysis } from '@/features/resume/hooks'

/** Results of one analysis. Polls while the background job is running. */
export default function AnalysisPage({ params }: { params: { analysisId: string } }) {
  const analysis = useAnalysis(params.analysisId)
  const data = analysis.data

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {data && (
        <Link href={`/dashboard/resume/${data.resume_id}`} className="flex items-center gap-1 text-sm text-muted hover:text-white">
          <ArrowLeft className="h-4 w-4" /> Back to resume
        </Link>
      )}
      {analysis.error && <ErrorBox error={analysis.error} />}
      {(analysis.isLoading || data?.status === 'queued' || data?.status === 'running') && (
        <Spinner label={data?.mode === 'jd' ? 'Matching your bullets to each requirement…' : 'Reviewing every bullet…'} />
      )}
      {data?.status === 'failed' && <ErrorBox error={new Error(data.error || 'The analysis failed. Please try again.')} />}

      {data?.status === 'done' && data.result && (
        <>
          {data.result.kind === 'jd' ? <JdMatchView match={data.result} /> : <GeneralReviewView review={data.result} />}
          <VersionCompare current={data} />
          <p className="text-xs text-muted">
            Analysed {formatDate(data.completed_at ?? data.created_at)} · model {data.model ?? 'n/a'} · prompts{' '}
            {Object.entries(data.prompt_versions ?? {}).map(([name, version]) => `${name} ${version}`).join(', ')}
          </p>
        </>
      )}
    </div>
  )
}
