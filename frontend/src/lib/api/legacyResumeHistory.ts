/**
 * Adapter for the legacy dashboard and progress pages (they are rebuilt in a later phase).
 * Returns resume v2 general reviews in the old "resume history" row shape those pages expect.
 */
import { api } from './client'
import type { components } from './types.gen'

type ResumeOverview = components['schemas']['ResumeOverview']

export async function fetchResumeHistory() {
  const overview = await api<ResumeOverview>('/resume/summary')
  return overview.recent
    .filter((analysis) => analysis.mode === 'general')
    .map((analysis) => ({
      id: analysis.id,
      result_id: analysis.id,
      candidate_name: analysis.resume_title,
      role_target: analysis.target_role ?? '',
      score: analysis.overall_score,
      skills: [] as string[],
      experience_level: '',
      created_at: analysis.created_at,
    }))
}
