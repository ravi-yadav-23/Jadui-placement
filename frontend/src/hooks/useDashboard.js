import { useState, useEffect, useMemo } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth';
import { fetchResumeHistory } from '@/lib/api/legacyResumeHistory'
import { fetchInterviewHistory } from '@/lib/api/legacyInterviewHistory'

export function useDashboard(userId, tasks, progress, chatContext) {
  const [resumeHistory, setResumeHistory] = useState([])
  const [interviewHistory, setInterviewHistory] = useState([])
  const [loadingStats, setLoadingStats] = useState(true)
  const [lastSyncedAt, setLastSyncedAt] = useState('')

  const [readinessData, setReadinessData] = useState([
    { subject: 'Resume', A: 0, value: 0, fullMark: 100 },
    { subject: 'Interview', A: 0, value: 0, fullMark: 100 },
    { subject: 'Consistency', A: 0, value: 0, fullMark: 100 },
  ])
  const [loadingRadar, setLoadingRadar] = useState(true)

  const todayTasks = useMemo(() => tasks.filter((t) => t.due === 'Today'), [tasks])
  const completedToday = useMemo(() => todayTasks.filter((t) => t.completed).length, [todayTasks])

  useEffect(() => {
    let mounted = true
    const loadStats = async () => {
      try {
        setLoadingStats(true)
        const [resumeRows, interviewRows] = await Promise.all([
          fetchResumeHistory().catch(() => []),     // resume v2 general reviews
          fetchInterviewHistory().catch(() => []),  // interview v2 completed sessions
        ])
        if (mounted) {
          setResumeHistory(resumeRows)
          setInterviewHistory(interviewRows)
        }
      } catch {
        if (mounted) {
          setResumeHistory([])
          setInterviewHistory([])
        }
      } finally {
        if (mounted) {
          setLoadingStats(false)
          setLastSyncedAt(new Date().toISOString())
        }
      }
    }

    const loadRadar = async () => {
      if (!userId) {
        setLoadingRadar(false)
        return
      }
      try {
        setLoadingRadar(true)
        const radarRes = await fetchWithAuth(`/api/system/readiness?user_id=${userId}`, { cache: 'no-store' })
        
        if (mounted) {
          if (radarRes.ok) {
            const radarJson = await radarRes.json()
            setReadinessData([
              { subject: 'Resume', A: radarJson.resume || 0, value: radarJson.resume || 0, fullMark: 100 },
              { subject: 'Interview', A: radarJson.interview || 0, value: radarJson.interview || 0, fullMark: 100 },
              { subject: 'Execution', A: radarJson.consistency || 0, value: radarJson.consistency || 0, fullMark: 100 },
            ])
          }
        }
      } catch (err) {
        console.error('Radar load failed', err)
      } finally {
        if (mounted) {
          setLoadingRadar(false)
        }
      }
    }

    loadStats()
    loadRadar()
    return () => { mounted = false }
  }, [userId])

  const derived = useMemo(() => {
    const latestResume = resumeHistory[0] || null
    const avgResume = resumeHistory.length > 0
      ? Math.round(resumeHistory.reduce((sum, item) => sum + Number(item.score || 0), 0) / resumeHistory.length)
      : 0
    const avgInterview = interviewHistory.length > 0
      ? Math.round(interviewHistory.reduce((sum, item) => sum + Number(item.overall_score || 0), 0) / interviewHistory.length)
      : 0
    const taskCompletion = todayTasks.length ? Math.round((completedToday / todayTasks.length) * 100) : 0
    const readiness = progress?.readinessScore || Math.round((avgResume * 0.45) + (avgInterview * 0.4) + (taskCompletion * 0.15))
    
    const skillBucket = {}
    resumeHistory.forEach((row) => {
      ;(row.skills || []).forEach((skill) => {
        const key = String(skill || '').trim()
        if (!key) return
        skillBucket[key] = (skillBucket[key] || 0) + 1
      })
    })
    const skillData = Object.entries(skillBucket)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, count]) => ({
        name,
        level: Math.min(95, 40 + count * 15),
      }))

    return { readiness, taskCompletion, avgInterview, avgResume, latestResume, skillData, totalResumes: resumeHistory.length, totalInterviews: interviewHistory.length }
  }, [resumeHistory, interviewHistory, todayTasks.length, completedToday, progress?.readinessScore])

  return {
    resumeHistory,
    interviewHistory,
    loadingStats,
    lastSyncedAt,
    readinessData,
    loadingRadar,
    derived,
    todayTasks,
    completedToday
  }
}
