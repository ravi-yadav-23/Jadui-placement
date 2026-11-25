'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { CalendarCheck, RefreshCw, SlidersHorizontal } from 'lucide-react'

import { Badge, Button, ButtonLink, EmptyState, Notice, PageHeader, Spinner, Tabs } from '@/components/ui'
import { useCurrentPlan, useReplan } from '@/features/planner/hooks'
import { CheckinCard, ProgressView, RoadmapView, WeekView } from '@/features/planner/components/PlanViews'
import { formatDay } from '@/lib/utils'

type Tab = 'week' | 'roadmap' | 'progress'

export default function PlannerPage() {
  return <Suspense fallback={<Spinner label="Loading…" />}><Planner /></Suspense>
}

function Planner() {
  const plan = useCurrentPlan()
  const replan = useReplan()
  const router = useRouter()
  const params = useSearchParams()
  const tab = (params.get('tab') as Tab) || 'week'
  const setTab = (t: Tab) => router.replace(t === 'week' ? '/dashboard/planner' : `/dashboard/planner?tab=${t}`, { scroll: false })

  if (plan.isLoading) return <Spinner label="Loading your plan…" />
  if (plan.error) return <Notice>{plan.error.message}</Notice>
  if (!plan.data) {
    return (
      <>
        <PageHeader title="Planner" />
        <EmptyState icon={<CalendarCheck className="h-6 w-6" />} title="Build your study plan"
          description="Five short questions (your goal, level, time and skills) turn into a dated roadmap across DSA, CS fundamentals, system design and projects."
          action={<ButtonLink href="/dashboard/planner/setup">Start (about 3 minutes)</ButtonLink>} />
      </>
    )
  }

  const data = plan.data
  return (
    <>
      <PageHeader title="Planner"
        description={<>Target {formatDay(data.target_date)} · {data.hours_per_week} h/week usable {data.feasibility.on_track
          ? <Badge tone="success" className="ml-1">On track</Badge> : <Badge tone="warning" className="ml-1">Behind</Badge>}</>}
        actions={<>
          <Button variant="secondary" size="sm" onClick={() => replan.mutate()} loading={replan.isPending} title="Rebuild the coming days from today">
            {!replan.isPending && <RefreshCw className="h-3.5 w-3.5" />} Re-plan
          </Button>
          <ButtonLink href="/dashboard/planner/setup" variant="secondary" size="sm"><SlidersHorizontal className="h-3.5 w-3.5" /> Edit answers</ButtonLink>
        </>} />
      {data.checkin_due && <div className="mb-6"><CheckinCard /></div>}
      <div className="mb-6">
        <Tabs<Tab> value={tab} onChange={setTab} tabs={[
          { value: 'week', label: 'This week' }, { value: 'roadmap', label: 'Roadmap' }, { value: 'progress', label: 'Progress' }]} />
      </div>
      {tab === 'week' && <WeekView />}
      {tab === 'roadmap' && <RoadmapView plan={data} />}
      {tab === 'progress' && <ProgressView plan={data} />}
    </>
  )
}
