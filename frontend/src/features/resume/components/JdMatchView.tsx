import { AlertOctagon, CheckCircle2, CircleDashed, MinusCircle, XCircle } from 'lucide-react'

import type { JdMatch, KnockoutResult, RequirementMatch } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { CopyButton, WithPlaceholders } from './GeneralReviewView'
import ScoreCard from './ScoreCard'

const STATUS = {
  strong: { icon: <CheckCircle2 className="h-4 w-4 text-success" />, label: 'Proven' },
  partial: { icon: <CircleDashed className="h-4 w-4 text-warning" />, label: 'Partial' },
  listed_only: { icon: <MinusCircle className="h-4 w-4 text-warning" />, label: 'Listed, not shown' },
  missing: { icon: <XCircle className="h-4 w-4 text-error" />, label: 'Missing' },
}

const TIER_STYLE = {
  strong: 'border-success/40 bg-success/10 text-success',
  good: 'border-primary/40 bg-primary/10 text-primary',
  stretch: 'border-warning/40 bg-warning/10 text-warning',
  not_a_fit: 'border-error/40 bg-error/10 text-error',
}

function KnockoutBanner({ knockouts }: { knockouts: KnockoutResult[] }) {
  const notOk = knockouts.filter((k) => k.status !== 'ok')
  if (notOk.length === 0) return null
  const conflict = notOk.some((k) => k.status === 'conflict')
  return (
    <section data-testid="knockouts" className={cn('rounded-xl border p-4',
      conflict ? 'border-error/40 bg-error/10' : 'border-warning/40 bg-warning/10')}>
      <p className={cn('flex items-center gap-2 font-semibold', conflict ? 'text-error' : 'text-warning')}>
        <AlertOctagon className="h-4 w-4" /> Eligibility {conflict ? 'conflict' : 'to confirm'}
      </p>
      <p className="mt-1 text-xs text-muted">These rules usually filter applications before anyone reads them.</p>
      <ul className="mt-2 space-y-1 text-sm text-white">
        {notOk.map((k) => <li key={k.type + k.jd_value}><b>{k.jd_value}:</b> {k.message}</li>)}
      </ul>
    </section>
  )
}

function RequirementRow({ match }: { match: RequirementMatch }) {
  const status = STATUS[match.status]
  return (
    <li className="rounded-lg border border-border bg-surface/40 p-3" data-testid="requirement">
      <div className="flex items-start gap-2">
        {status.icon}
        <div className="flex-1">
          <p className="text-sm text-white">
            {match.text}
            <span className="ml-2 rounded border border-border px-1.5 text-[10px] uppercase text-muted">{match.kind}</span>
          </p>
          <p className="mt-0.5 text-xs text-muted">{status.label}: {match.reason}</p>
          {match.evidence?.map((ev) => (
            <blockquote key={ev.bullet_id} className="mt-1 border-l-2 border-success/50 pl-2 text-xs italic text-muted">
              “{ev.text}”
            </blockquote>
          ))}
        </div>
      </div>
    </li>
  )
}

export default function JdMatchView({ match }: { match: JdMatch }) {
  const musts = match.requirements.filter((r) => r.kind === 'must')
  const nices = match.requirements.filter((r) => r.kind === 'nice')

  return (
    <div className="space-y-6">
      <KnockoutBanner knockouts={match.knockouts ?? []} />

      <section className={cn('rounded-xl border p-4', TIER_STYLE[match.tier])} data-testid="tier">
        <p className="text-sm uppercase tracking-wide">{match.tier.replace(/_/g, ' ')}</p>
        <p className="mt-1 text-white">{match.tier_message}</p>
      </section>

      <ScoreCard
        title={`Match: ${match.jd_title}${match.jd_company ? ` · ${match.jd_company}` : ''}`}
        score={match.overall_score}
        subScores={match.sub_scores}
        footnote="Every ✓ quotes the bullet that proves it. Being listed in your skills section alone counts as half."
      />

      <section className="card-base space-y-3">
        <h2 className="text-lg font-semibold text-white">Requirements</h2>
        <ul className="space-y-2">{musts.map((m) => <RequirementRow key={m.requirement_id} match={m} />)}</ul>
        {nices.length > 0 && (
          <>
            <h3 className="pt-2 text-sm font-semibold uppercase tracking-wide text-muted">Nice to have</h3>
            <ul className="space-y-2">{nices.map((m) => <RequirementRow key={m.requirement_id} match={m} />)}</ul>
          </>
        )}
      </section>

      {((match.keywords_to_surface?.length ?? 0) > 0 || (match.missing_keywords?.length ?? 0) > 0) && (
        <section className="card-base space-y-2 text-sm">
          <h2 className="text-lg font-semibold text-white">Keywords</h2>
          {(match.keywords_to_surface?.length ?? 0) > 0 && (
            <p className="text-white">You have these but no bullet shows them, so add them where they&apos;re true:{' '}
              <span className="text-warning">{match.keywords_to_surface?.join(', ')}</span></p>
          )}
          {(match.missing_keywords?.length ?? 0) > 0 && (
            <p className="text-muted">Not on your resume (don&apos;t add unless true): {match.missing_keywords?.join(', ')}</p>
          )}
        </section>
      )}

      {((match.tailored_bullets?.length ?? 0) > 0 || match.summary_suggestion) && (
        <section className="card-base space-y-3">
          <h2 className="text-lg font-semibold text-white">Tailoring suggestions</h2>
          {match.summary_suggestion && (
            <div className="rounded-lg border border-primary/30 bg-primary/5 p-3 text-sm text-white">
              <div className="flex justify-between text-xs text-primary">Summary line <CopyButton text={match.summary_suggestion} /></div>
              <p className="mt-1"><WithPlaceholders text={match.summary_suggestion} /></p>
            </div>
          )}
          {match.tailored_bullets?.map((t) => (
            <div key={t.bullet_id} className="rounded-lg border border-border bg-surface/40 p-3 text-sm">
              <p className="text-muted line-through decoration-muted/50">{t.original}</p>
              <div className="mt-1 flex items-start justify-between gap-2">
                <p className="text-white"><WithPlaceholders text={t.rewrite} /></p>
                <CopyButton text={t.rewrite} />
              </div>
            </div>
          ))}
        </section>
      )}

      {(match.gaps?.length ?? 0) > 0 && (
        <section className="card-base text-sm">
          <h2 className="text-lg font-semibold text-white">Gaps saved to your plan</h2>
          <p className="mt-1 text-muted">Missing requirements. Learn them, build something, then re-run the match.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {match.gaps?.map((g) => <span key={g} className="rounded-full border border-error/30 px-2 py-0.5 text-error">{g}</span>)}
          </div>
        </section>
      )}
    </div>
  )
}
