// React Query hooks for all TerraBot API endpoints

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/api-client'
import type {
  Job,
  Template,
  Approval,
  HealthStatus,
  ProviderConfig,
} from '../types/api-types'

// --- Query keys ---
export const queryKeys = {
  templates: (provider?: string) => ['templates', provider] as const,
  template: (name: string) => ['template', name] as const,
  jobs: (status?: string) => ['jobs', status] as const,
  job: (id: string) => ['job', id] as const,
  approvals: () => ['approvals'] as const,
  health: () => ['health'] as const,
}

// --- Read hooks ---
// Flatten API template shape {metadata: {...}, variables: [...]} into flat Template
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function flattenTemplate(raw: any): Template {
  const meta = raw.metadata ?? raw
  return {
    name: meta.name ?? meta.display_name ?? '',
    provider: meta.provider ?? '',
    description: meta.description ?? '',
    tags: meta.tags ?? [],
    variables: (raw.variables ?? []).map((v: any) => ({
      ...v,
      required: v.required ?? (v.default === null || v.default === undefined),
    })),
    estimated_cost: meta.estimated_cost ?? null,
  }
}

export function useTemplates(provider?: string) {
  return useQuery({
    queryKey: queryKeys.templates(provider),
    queryFn: async () => {
      const res = await apiClient.get<{ templates: any[] }>('/api/templates', provider ? { provider } : undefined)
      return (res.templates ?? []).map(flattenTemplate)
    },
  })
}

export function useTemplate(name: string) {
  return useQuery({
    queryKey: queryKeys.template(name),
    queryFn: async () => {
      const raw = await apiClient.get<any>(`/api/templates/${name}`)
      return flattenTemplate(raw)
    },
    enabled: !!name,
  })
}

export function useJobs(status?: string) {
  return useQuery({
    queryKey: queryKeys.jobs(status),
    queryFn: async () => {
      const res = await apiClient.get<{ jobs: Job[] }>('/api/jobs', status ? { status } : undefined)
      return res.jobs ?? []
    },
    refetchInterval: 5000,
  })
}

export function useJob(id: string) {
  return useQuery({
    queryKey: queryKeys.job(id),
    queryFn: () => apiClient.get<Job>(`/api/jobs/${id}`),
    enabled: !!id,
    refetchInterval: 3000,
  })
}

export function useApprovals() {
  return useQuery({
    queryKey: queryKeys.approvals(),
    queryFn: async () => {
      const res = await apiClient.get<{ approvals: Approval[] }>('/api/approvals')
      return res.approvals ?? []
    },
    refetchInterval: 5000,
  })
}

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => apiClient.get<HealthStatus>('/api/health'),
    refetchInterval: 30000,
  })
}

// --- Mutation hooks ---
export function usePlanMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { template: string; variables: Record<string, unknown> }) =>
      apiClient.post<Job>('/api/plan', payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useApplyMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { template: string; variables: Record<string, unknown> }) =>
      apiClient.post<Job>('/api/apply', payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useDestroyMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workspace: string) =>
      apiClient.post<Job>('/api/destroy', { workspace }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useApprovalDecision() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, approved, reason }: { id: string; approved: boolean; reason?: string }) =>
      apiClient.post<Approval>(`/api/approvals/${id}/decide`, { approved, reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useRenderTemplate() {
  return useMutation({
    mutationFn: (payload: { template: string; variables: Record<string, unknown> }) =>
      apiClient.post<{ rendered: string }>('/api/templates/render', payload),
  })
}

export function useSaveProviderConfig() {
  return useMutation({
    mutationFn: (config: ProviderConfig) =>
      apiClient.post<{ ok: boolean }>('/api/config/provider', config),
  })
}
