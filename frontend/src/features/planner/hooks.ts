/** React Query hooks for the planner. Every change refreshes the plan, its tasks and the Today dashboard. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, ApiError } from '@/lib/api/client'
import type { CheckinRequest, PlanDetail, PlannerProfile, PlanPreview, PlanTask, ProfileResponse } from '@/lib/api/types'

export const plannerKeys = {
  profile: ['planner-profile'] as const,
  plan: ['plan'] as const,
  tasks: (start: string, end: string) => ['plan-tasks', start, end] as const,
}

function useInvalidatePlanner() {
  const client = useQueryClient()
  return () => {
    client.invalidateQueries({ queryKey: plannerKeys.plan })
    client.invalidateQueries({ queryKey: ['plan-tasks'] })
    client.invalidateQueries({ queryKey: ['dashboard'] })
  }
}

export function usePlannerProfile() {
  return useQuery({ queryKey: plannerKeys.profile, queryFn: () => api<ProfileResponse>('/planner/profile') })
}

/** The active plan, or null if the user has none yet (404 is a normal state here). */
export function useCurrentPlan() {
  return useQuery({
    queryKey: plannerKeys.plan,
    queryFn: async () => {
      try {
        return await api<PlanDetail>('/plans/current')
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    // The AI roadmap text is written a few seconds after the plan is created: check back briefly.
    refetchInterval: (query) => {
      const plan = query.state.data
      const fresh = plan && Date.now() - new Date(plan.created_at).getTime() < 30_000
      return plan?.summary?.source === 'template' && fresh ? 3000 : false
    },
  })
}

export function usePlanTasks(start: string, end: string, enabled = true) {
  return useQuery({
    queryKey: plannerKeys.tasks(start, end),
    queryFn: () => api<PlanTask[]>(`/plans/current/tasks?start=${start}&end=${end}`),
    enabled,
  })
}

export function usePreviewPlan() {
  return useMutation({
    mutationFn: (profile: PlannerProfile) => api<PlanPreview>('/plans/preview', { method: 'POST', body: JSON.stringify(profile) }),
  })
}

export function useCreatePlan() {
  const invalidate = useInvalidatePlanner()
  const client = useQueryClient()
  return useMutation({
    mutationFn: (profile: PlannerProfile) => api<PlanDetail>('/plans', { method: 'POST', body: JSON.stringify(profile) }),
    onSuccess: (plan) => {
      client.setQueryData(plannerKeys.plan, plan)
      client.invalidateQueries({ queryKey: plannerKeys.profile })
      invalidate()
    },
  })
}

export function useUpdateTask() {
  const invalidate = useInvalidatePlanner()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: PlanTask['status'] }) =>
      api<PlanTask>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
    onSuccess: invalidate,
  })
}

export function useMoveTask() {
  const invalidate = useInvalidatePlanner()
  return useMutation({
    mutationFn: ({ id, date }: { id: string; date: string }) =>
      api<PlanTask>(`/tasks/${id}/move`, { method: 'POST', body: JSON.stringify({ date }) }),
    onSuccess: invalidate,
  })
}

export function useReplan() {
  const invalidate = useInvalidatePlanner()
  return useMutation({ mutationFn: () => api<PlanDetail>('/plans/current/replan', { method: 'POST' }), onSuccess: invalidate })
}

export function useCheckin() {
  const invalidate = useInvalidatePlanner()
  return useMutation({
    mutationFn: (body: CheckinRequest) => api<PlanDetail>('/plans/current/checkins', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: invalidate,
  })
}
