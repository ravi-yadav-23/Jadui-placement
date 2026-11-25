/** Coach chat + dashboard queries. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api/client'
import type { CoachMessage, DashboardOverview } from '@/lib/api/types'

export function useDashboard() {
  return useQuery({ queryKey: ['dashboard'], queryFn: () => api<DashboardOverview>('/dashboard') })
}

export function useCoachMessages() {
  return useQuery({ queryKey: ['coach'], queryFn: () => api<CoachMessage[]>('/coach/messages') })
}

export function useSendMessage() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (content: string) => api<CoachMessage>('/coach/messages', { method: 'POST', body: JSON.stringify({ content }) }),
    // Show the question immediately; the server stores it together with the reply.
    onMutate: (content) => {
      const previous = client.getQueryData<CoachMessage[]>(['coach']) ?? []
      const pending: CoachMessage = { id: 'pending', role: 'user', content, actions: [], created_at: new Date().toISOString() }
      client.setQueryData(['coach'], [...previous, pending])
      return { previous }
    },
    onError: (_error, _content, context) => client.setQueryData(['coach'], context?.previous ?? []),
    onSettled: () => client.invalidateQueries({ queryKey: ['coach'] }),
  })
}

export function useClearCoach() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/coach/messages', { method: 'DELETE' }),
    onSuccess: () => client.setQueryData(['coach'], []),
  })
}
