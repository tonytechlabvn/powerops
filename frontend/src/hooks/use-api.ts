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

// Map API job shape (workspace_dir) to frontend Job shape (workspace)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapJob(raw: any): Job {
  return {
    ...raw,
    workspace: raw.workspace ?? raw.workspace_dir ?? '',
  }
}

export function useJobs(status?: string, includeHidden?: boolean) {
  return useQuery({
    queryKey: [...queryKeys.jobs(status), includeHidden ?? false],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (status) params.status = status
      if (includeHidden) params.include_hidden = 'true'
      const res = await apiClient.get<{ jobs: any[] }>('/api/jobs', params)
      return (res.jobs ?? []).map(mapJob)
    },
    refetchInterval: 5000,
  })
}

export function useJob(id: string) {
  return useQuery({
    queryKey: queryKeys.job(id),
    queryFn: async () => {
      const raw = await apiClient.get<any>(`/api/jobs/${id}`)
      return mapJob(raw)
    },
    enabled: !!id,
    refetchInterval: 3000,
  })
}

// Map API approval shape to frontend Approval type
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapApproval(raw: any): Approval {
  const ps = raw.plan_summary
  // API may return [] or null or an object — normalize to PlanSummary | null
  const planSummary = ps && typeof ps === 'object' && !Array.isArray(ps) && 'adds' in ps
    ? ps
    : null
  return {
    ...raw,
    plan_summary: planSummary,
  }
}

export function useApprovals() {
  return useQuery({
    queryKey: queryKeys.approvals(),
    queryFn: async () => {
      const res = await apiClient.get<{ approvals: any[] }>('/api/approvals')
      return (res.approvals ?? []).map(mapApproval)
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
      apiClient.post<{ job_id: string; workspace: string; stream_url: string }>('/api/deploy', payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useAutoDeployMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      instance_name?: string
      instance_type?: string
      os_type?: string
      environment?: string
    }) =>
      apiClient.post<{ job_id: string; workspace: string; stream_url: string }>(
        '/api/deploy/auto', payload
      ),
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
      apiClient.post<{ job_id: string }>('/api/terraform/destroy', {
        workspace,
        confirmation: 'destroy',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useHideJobMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) =>
      apiClient.patch<Job>(`/api/jobs/${jobId}/hide`),
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

export function useProviderConfig(provider: string) {
  return useQuery({
    queryKey: ['providerConfig', provider],
    queryFn: () =>
      apiClient.get<{ provider: string; configured: boolean; credentials_redacted: Record<string, string> }>(
        '/api/config/provider', { provider }
      ),
  })
}

export function useSaveProviderConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: ProviderConfig) =>
      apiClient.post<{ ok: boolean }>('/api/config/provider', {
        provider: config.provider,
        credentials: config.config,
      }),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['providerConfig', variables.provider] })
    },
  })
}
