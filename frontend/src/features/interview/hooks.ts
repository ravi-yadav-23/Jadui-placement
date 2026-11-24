/**
 * React Query hooks for mock interviews.
 *
 * Planning (resume/JD tracks) and answer judging run in the background on the server.
 * useInterview() polls every 1.5 s while the interview is being planned or an answer is being judged.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api/client'
import type { AnswerRequest, CreateInterview, InterviewDetail, InterviewSummary } from '@/lib/api/types'

const POLL_MS = 1500

export const interviewKeys = {
  list: ['interviews'] as const,
  one: (id: string) => ['interviews', id] as const,
}

function isWorking(data?: InterviewDetail) {
  if (!data) return false
  const last = data.turns[data.turns.length - 1]
  return data.status === 'planning' || last?.status === 'evaluating'
}

export function useInterviews() {
  return useQuery({ queryKey: interviewKeys.list, queryFn: () => api<InterviewSummary[]>('/interviews') })
}

export function useInterview(id: string) {
  return useQuery({
    queryKey: interviewKeys.one(id),
    queryFn: () => api<InterviewDetail>(`/interviews/${id}`),
    refetchInterval: (query) => (isWorking(query.state.data) ? POLL_MS : false),
  })
}

export function useCreateInterview() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateInterview) => api<InterviewDetail>('/interviews', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: (data) => {
      client.setQueryData(interviewKeys.one(data.id), data)
      client.invalidateQueries({ queryKey: interviewKeys.list, exact: true })
    },
  })
}

/** Every action on a running interview returns the updated interview; we put it straight in the cache. */
function useInterviewAction<V>(id: string, request: (vars: V) => Promise<InterviewDetail>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: (data) => {
      client.setQueryData(interviewKeys.one(id), data)
      if (data.status === 'completed') client.invalidateQueries({ queryKey: interviewKeys.list, exact: true })
    },
  })
}

export function useAnswer(id: string) {
  return useInterviewAction(id, ({ turnId, body }: { turnId: string; body: AnswerRequest }) =>
    api<InterviewDetail>(`/interviews/${id}/turns/${turnId}/answer`, { method: 'POST', body: JSON.stringify(body) }))
}

export function useRetry(id: string) {
  return useInterviewAction(id, (turnId: string) =>
    api<InterviewDetail>(`/interviews/${id}/turns/${turnId}/retry`, { method: 'POST' }))
}

export function useSkip(id: string) {
  return useInterviewAction(id, () => api<InterviewDetail>(`/interviews/${id}/skip`, { method: 'POST' }))
}

export function useFinish(id: string) {
  return useInterviewAction(id, () => api<InterviewDetail>(`/interviews/${id}/finish`, { method: 'POST' }))
}

export function useDeleteInterview() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<void>(`/interviews/${id}`, { method: 'DELETE' }),
    onSuccess: () => client.invalidateQueries({ queryKey: interviewKeys.list, exact: true }),
  })
}
