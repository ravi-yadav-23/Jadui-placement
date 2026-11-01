import { useEffect, useRef } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export function useStatePersistence(readyToPersist, state) {
  const persistTimerRef = useRef(null)

  useEffect(() => {
    if (!readyToPersist || !state.user?.id) return
    if (persistTimerRef.current) clearTimeout(persistTimerRef.current)
    
    persistTimerRef.current = setTimeout(async () => {
      try {
        await fetchWithAuth('/api/system/state', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: state.user.id,
            tasks: state.tasks,
            roadmap: state.roadmap,
            notifications: state.notifications,
            skill_gaps: state.skillGaps,
            chat_context: state.chatContext || {},
            chat_history: state.chatHistory || [],
            chat_sessions: state.chatSessions || [],
            active_chat_session_id: state.activeChatSessionId || '',
          }),
        })
      } catch {
        // no-op persistence fallback
      }
    }, 500)

    return () => {
      if (persistTimerRef.current) clearTimeout(persistTimerRef.current)
    }
  }, [
    readyToPersist, 
    state.user?.id, 
    state.tasks, 
    state.roadmap, 
    state.notifications, 
    state.skillGaps, 
    state.chatContext, 
    state.chatHistory, 
    state.chatSessions, 
    state.activeChatSessionId
  ])
}
