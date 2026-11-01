import { useState } from 'react'
import { ACTIONS } from '@/context/AppContext'
import { fetchWithAuth } from '@/lib/fetchWithAuth';

export function useDashboardActions(state, dispatch, derived) {
  const [syncStatus, setSyncStatus] = useState('idle')
  const [goalSaved, setGoalSaved] = useState(false)
  const [generatingPlan, setGeneratingPlan] = useState(false)

  const saveStateServer = async (nextPayload) => {
    if (!state.user?.id) return
    try {
      setSyncStatus('syncing')
      const response = await fetchWithAuth('/api/system/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: state.user.id,
          tasks: nextPayload.tasks ?? state.tasks,
          roadmap: nextPayload.roadmap ?? state.roadmap,
          notifications: nextPayload.notifications ?? state.notifications,
          skill_gaps: nextPayload.skillGaps ?? state.skillGaps,
          chat_context: nextPayload.chatContext ?? state.chatContext ?? {},
          chat_history: nextPayload.chatHistory ?? state.chatHistory ?? [],
          chat_sessions: nextPayload.chatSessions ?? state.chatSessions ?? [],
          active_chat_session_id: nextPayload.activeChatSessionId ?? state.activeChatSessionId ?? '',
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.error || 'Failed to sync')
      }
      setSyncStatus('synced')
      return data
    } catch {
      setSyncStatus('error')
      return null
    }
  }

  const saveGoal = async (goalRole, goalDate) => {
    const mergedContext = {
      ...(state.chatContext || {}),
      targetRole: goalRole,
      targetPlacementDate: goalDate,
    }
    const payload = {
      tasks: state.tasks,
      roadmap: state.roadmap,
      notifications: state.notifications,
      skillGaps: state.skillGaps,
      chatContext: mergedContext,
      chatHistory: state.chatHistory,
      chatSessions: state.chatSessions,
      activeChatSessionId: state.activeChatSessionId,
    }
    dispatch({
      type: ACTIONS.SET_SYSTEM_INSIGHTS,
      payload,
    })
    await saveStateServer(payload)
    setGoalSaved(true)
    setTimeout(() => setGoalSaved(false), 1500)
  }

  const generateTodayPlan = async (weakestTwoSkills) => {
    setGeneratingPlan(true)
    const focusA = weakestTwoSkills[0] || 'Core Fundamentals'
    const focusB = weakestTwoSkills[1] || 'Interview Clarity'
    const generatedTasks = [
      {
        id: `plan-${Date.now()}-1`,
        title: `Deep practice: ${focusA} (45 min)`,
        category: 'Core',
        completed: false,
        due: 'Today',
      },
      {
        id: `plan-${Date.now()}-2`,
        title: `Targeted drill: ${focusB} (2 focused problems)`,
        category: 'DSA',
        completed: false,
        due: 'Today',
      },
      {
        id: `plan-${Date.now()}-3`,
        title: 'Mock response practice using STAR format (20 min)',
        category: 'Interview',
        completed: false,
        due: 'Today',
      },
    ]
    const deduped = [...generatedTasks, ...state.tasks.filter((t) => t.due !== 'Today')]
    const payload = {
      tasks: deduped,
      roadmap: state.roadmap,
      notifications: [
        {
          id: `notif-plan-${Date.now()}`,
          title: 'Today plan generated',
          body: `Your focus plan is ready: ${focusA} + ${focusB}.`,
          read: false,
        },
        ...(state.notifications || []),
      ].slice(0, 20),
      skillGaps: state.skillGaps,
      chatContext: state.chatContext,
      chatHistory: state.chatHistory,
      chatSessions: state.chatSessions,
      activeChatSessionId: state.activeChatSessionId,
    }
    dispatch({
      type: ACTIONS.SET_SYSTEM_INSIGHTS,
      payload,
    })
    await saveStateServer(payload)
    setTimeout(() => setGeneratingPlan(false), 600)
  }

  return {
    syncStatus,
    goalSaved,
    generatingPlan,
    saveGoal,
    generateTodayPlan
  }
}
