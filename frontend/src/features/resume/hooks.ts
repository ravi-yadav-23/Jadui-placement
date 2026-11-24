/**
 * React Query hooks for the resume screener.
 *
 * Background jobs (upload processing, JD parsing, analyses) return immediately with a status;
 * the detail hooks poll every 1.5 s while the status is still queued/processing/running.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api/client'
import type {
  AnalysisDetail,
  AnalysisSummary,
  CreateAnalysis,
  JdDetail,
  JdSummary,
  ResumeDetail,
  ResumeProfile,
  ResumeSummary,
} from '@/lib/api/types'

const POLL_MS = 1500
const isPending = (status?: string) => status === 'queued' || status === 'processing' || status === 'running'

export const keys = {
  resumes: ['resumes'] as const,
  resume: (id: string) => ['resumes', id] as const,
  jds: ['jds'] as const,
  jd: (id: string) => ['jds', id] as const,
  analyses: (resumeId?: string) => ['analyses', { resumeId }] as const,
  analysis: (id: string) => ['analysis', id] as const,
}

// ---------- Resumes ----------

export function useResumes() {
  return useQuery({ queryKey: keys.resumes, queryFn: () => api<ResumeSummary[]>('/resumes') })
}

export function useResume(id: string) {
  return useQuery({
    queryKey: keys.resume(id),
    queryFn: () => api<ResumeDetail>(`/resumes/${id}`),
    refetchInterval: (query) => (isPending(query.state.data?.status) ? POLL_MS : false),
  })
}

export function useUploadResume() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ file, title }: { file: File; title?: string }) => {
      const form = new FormData()
      form.append('file', file)
      if (title) form.append('title', title)
      return api<ResumeSummary>('/resumes', { method: 'POST', body: form })
    },
    onSuccess: () => client.invalidateQueries({ queryKey: keys.resumes }),
  })
}

export function useUpdateProfile(id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (profile: ResumeProfile) =>
      api<ResumeDetail>(`/resumes/${id}/profile`, { method: 'PATCH', body: JSON.stringify(profile) }),
    onSuccess: (data) => client.setQueryData(keys.resume(id), data),
  })
}

export function useDeleteResume() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api<void>(`/resumes/${id}`, { method: 'DELETE' }),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.resumes }),
  })
}

export function useResumeFileUrl(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ['resume-file', id],
    queryFn: () => api<{ url: string }>(`/resumes/${id}/file`),
    enabled,
    staleTime: 4 * 60 * 1000, // signed URLs live 5 minutes
  })
}

// ---------- Job descriptions ----------

export function useJds() {
  return useQuery({ queryKey: keys.jds, queryFn: () => api<JdSummary[]>('/jds') })
}

export function useJd(id: string | null) {
  return useQuery({
    queryKey: keys.jd(id ?? ''),
    queryFn: () => api<JdDetail>(`/jds/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) => (isPending(query.state.data?.status) ? POLL_MS : false),
  })
}

export function useCreateJd() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: { raw_text: string; title?: string; company?: string }) =>
      api<JdSummary>('/jds', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.jds }),
  })
}

// ---------- Analyses ----------

export function useAnalyses(resumeId?: string) {
  return useQuery({
    queryKey: keys.analyses(resumeId),
    queryFn: () => api<AnalysisSummary[]>(`/analyses${resumeId ? `?resume_id=${resumeId}` : ''}`),
  })
}

export function useAnalysis(id: string) {
  return useQuery({
    queryKey: keys.analysis(id),
    queryFn: () => api<AnalysisDetail>(`/analyses/${id}`),
    refetchInterval: (query) => (isPending(query.state.data?.status) ? POLL_MS : false),
  })
}

export function useCreateAnalysis() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateAnalysis) => api<AnalysisSummary>('/analyses', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['analyses'] }),
  })
}
