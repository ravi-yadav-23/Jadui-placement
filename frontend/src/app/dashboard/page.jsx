'use client'

export const dynamic = 'force-dynamic'

import { useEffect, useMemo, useState } from 'react'
import { Target, CheckSquare, Mic, Flame, Sparkles } from 'lucide-react'
import StatCard from '@/components/dashboard/StatCard'
import { useApp } from '@/context/AppContext'
import { cn } from '@/lib/utils'

import { useDashboard } from '@/hooks/useDashboard'
import { useDashboardActions } from '@/hooks/useDashboardActions'

import ReadinessRadar from '@/components/dashboard/ReadinessRadar'
import Link from 'next/link'
import CoachSummary from '@/components/dashboard/CoachSummary'
import RiskAlerts from '@/components/dashboard/RiskAlerts'
import TaskOverview from '@/components/dashboard/TaskOverview'
import GoalSettingCard from '@/components/dashboard/GoalSettingCard'
import AutoPriorityCard from '@/components/dashboard/AutoPriorityCard'
import SkillSnapshotCard from '@/components/dashboard/SkillSnapshotCard'
import RecentActivityCard from '@/components/dashboard/RecentActivityCard'
import TopSkillGapsCard from '@/components/dashboard/TopSkillGapsCard'
import QuickActions from '@/components/dashboard/QuickActions'

export default function DashboardPage() {
  const { state, dispatch } = useApp()
  const { tasks, skillGaps, chatContext } = state
  
  const [goalRole, setGoalRole] = useState('')
  const [goalDate, setGoalDate] = useState('')
  const [isMounted, setIsMounted] = useState(false)

  const {
    resumeHistory,
    interviewHistory,
    loadingStats,
    lastSyncedAt,
    readinessData,
    derived,
    todayTasks,
    completedToday
  } = useDashboard(state.user?.id, tasks, state.progress, chatContext)

  const {
    syncStatus,
    goalSaved,
    generatingPlan,
    saveGoal,
    generateTodayPlan
  } = useDashboardActions(state, dispatch, derived)

  const weakestTwoSkills = useMemo(() => {
    if (skillGaps?.length) return skillGaps.slice(0, 2)
    return (derived.skillData || [])
      .slice()
      .sort((a, b) => a.level - b.level)
      .slice(0, 2)
      .map((s) => s.name)
  }, [skillGaps, derived.skillData])

  const readinessBand = useMemo(() => {
    if (derived.readiness >= 75) return { label: 'On Track', tone: 'text-success', note: 'Keep consistency and start harder mocks.' }
    if (derived.readiness >= 50) return { label: 'Needs Focus', tone: 'text-warning', note: 'Close top skill gaps and improve interview consistency.' }
    return { label: 'At Risk', tone: 'text-error', note: 'Prioritize fundamentals and daily execution this week.' }
  }, [derived.readiness])

  const nextBestAction = useMemo(() => {
    if (!resumeHistory.length) return 'Upload your resume to unlock personalized skill-gap insights.'
    if (!interviewHistory.length) return 'Take your first mock interview to benchmark communication and clarity.'
    if (todayTasks.length && completedToday < todayTasks.length) return 'Complete remaining today tasks to increase readiness quickly.'
    if (skillGaps?.length) return `Focus on top gap: ${skillGaps[0]}. Add one targeted practice block today.`
    return 'Review your latest feedback and push one high-impact improvement today.'
  }, [resumeHistory.length, interviewHistory.length, todayTasks.length, completedToday, skillGaps])

  const riskAlerts = useMemo(() => {
    const alerts = []
    if (!resumeHistory.length) alerts.push('No resume analysis found yet.')
    if (!interviewHistory.length) alerts.push('No interview practice session recorded yet.')
    if (todayTasks.length > 0 && completedToday === 0) alerts.push('No task completed today.')
    if (skillGaps?.length >= 4) alerts.push('Multiple skill gaps detected. Prioritize top 2 this week.')
    return alerts
  }, [resumeHistory.length, interviewHistory.length, todayTasks.length, completedToday, skillGaps])

  useEffect(() => {
    setGoalRole(chatContext?.targetRole || '')
    setGoalDate(chatContext?.targetPlacementDate || '')
  }, [chatContext?.targetRole, chatContext?.targetPlacementDate])

  useEffect(() => {
    setIsMounted(true)
  }, [])

  return (
    <div className={`max-w-7xl mx-auto space-y-8 transition-opacity duration-700 ${isMounted ? 'opacity-100' : 'opacity-0'} relative`}>
      {/* Background orbs for premium feel */}
      <div className="absolute top-[-100px] right-[-100px] w-96 h-96 bg-primary/10 blur-[100px] rounded-full -z-10 animate-pulse" />
      <div className="absolute bottom-[200px] left-[-100px] w-72 h-72 bg-secondary/10 blur-[80px] rounded-full -z-10" />

      {/* Greeting */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight">
            Good {isMounted ? getGreeting() : '...'},{' '}
            <span className="gradient-text-primary">
              {state.user?.user_metadata?.full_name?.split(' ')[0] || 'Candidate'} 👋
            </span>
          </h1>
          <p className="text-muted text-sm mt-1 font-medium italic opacity-80">
            Insights synced and parsed by Jadui Intelligence Layer.
          </p>
          <div className="flex items-center gap-3 mt-3">
            <span className={cn(
              'px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-all duration-300',
              syncStatus === 'synced' && 'bg-success/10 border-success/30 text-success',
              syncStatus === 'syncing' && 'bg-primary/10 border-primary/30 text-primary animate-pulse',
              syncStatus === 'error' && 'bg-error/10 border-error/30 text-error',
              syncStatus === 'idle' && 'bg-surface/50 border-border text-muted'
            )}>
              {syncStatus === 'syncing' ? 'Analyzing...' : syncStatus === 'error' ? 'Sync Error' : 'System Ready'}
            </span>
            <p className="text-[11px] text-muted font-medium">
              {isMounted && lastSyncedAt
                ? `Updated ${new Date(lastSyncedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                : 'Hydrating profile...'}
            </p>
          </div>
        </div>
        
        <button 
          onClick={() => window.location.reload()}
          className="btn-outline px-4 py-2 mt-4 md:mt-0"
        >
          <Sparkles className="w-4 h-4 text-primary" />
          Full Re-Sync
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          id="stat-readiness"
          title="Readiness Score"
          value={`${derived.readiness}%`}
          subtitle={loadingStats ? 'Syncing your latest records...' : 'Computed from resume + interview + tasks'}
          icon={Target}
          color="primary"
          trend="up"
          trendValue={derived.totalResumes || derived.totalInterviews ? `${derived.totalResumes} resumes, ${derived.totalInterviews} interviews` : 'No records yet'}
        />
        <StatCard
          id="stat-tasks"
          title="Tasks Complete"
          value={`${derived.taskCompletion}%`}
          subtitle={`${completedToday}/${todayTasks.length} tasks today`}
          icon={CheckSquare}
          color="success"
          trend="up"
          trendValue={`${completedToday} done`}
        />
        <StatCard
          id="stat-interview"
          title="Interview Score"
          value={`${derived.avgInterview}%`}
          subtitle={interviewHistory[0] ? `Last role: ${interviewHistory[0].role}` : 'No interview attempt yet'}
          icon={Mic}
          color="accent"
          trend="up"
          trendValue={interviewHistory.length ? `${interviewHistory.length} sessions` : 'Start first interview'}
        />
        <StatCard
          id="stat-resume"
          title="Resume Score"
          value={`${derived.avgResume}%`}
          subtitle={derived.latestResume ? `Target role: ${derived.latestResume.role_target}` : 'Upload resume to start'}
          icon={Flame}
          color="warning"
          trend="up"
          trendValue={derived.latestResume?.experience_level ? `${derived.latestResume.experience_level} level` : 'No resume yet'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ReadinessRadar readinessData={readinessData} />
        <Link href="/dashboard/resume" className="card-base flex flex-col justify-between hover:border-primary/50">
          <div>
            <p className="text-lg font-semibold text-white">Resume Screener</p>
            <p className="mt-2 text-sm text-muted">
              Check how parsers read your resume, get truth-guarded bullet feedback, and match it against a job description.
            </p>
          </div>
          <span className="mt-4 text-sm text-primary">Open the screener →</span>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <CoachSummary readinessBand={readinessBand} nextBestAction={nextBestAction} />
        <RiskAlerts riskAlerts={riskAlerts} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GoalSettingCard 
          goalRole={goalRole} setGoalRole={setGoalRole} 
          goalDate={goalDate} setGoalDate={setGoalDate} 
          saveGoal={saveGoal} goalSaved={goalSaved} 
        />
        <AutoPriorityCard 
          weakestTwoSkills={weakestTwoSkills} 
          generateTodayPlan={generateTodayPlan} 
          generatingPlan={generatingPlan} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <TaskOverview todayTasks={todayTasks} completedToday={completedToday} />
        <SkillSnapshotCard skillData={derived.skillData} />
      </div>

      <RecentActivityCard resumeHistory={resumeHistory} interviewHistory={interviewHistory} />
      <TopSkillGapsCard skillGaps={skillGaps} />
      <QuickActions />
    </div>
  )
}

function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'morning'
  if (hour < 17) return 'afternoon'
  return 'evening'
}
