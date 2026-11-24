/**
 * Adapter for the legacy dashboard and progress pages (they are rebuilt in a later phase).
 * Returns completed v2 mock interviews in the old "interview history" row shape those pages expect.
 */
import { TRACKS } from '@/features/interview/labels'
import { api } from './client'
import type { InterviewSummary } from './types'

export async function fetchInterviewHistory() {
  const interviews = await api<InterviewSummary[]>('/interviews')
  return interviews
    .filter((i) => i.status === 'completed' && i.score != null)
    .map((i) => ({
      session_id: i.id,
      role: i.target_role || TRACKS[i.track].label,
      overall_score: i.score as number,
      created_at: i.created_at,
    }))
}
