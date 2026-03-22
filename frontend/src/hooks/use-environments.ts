// React Query hooks for Environment CRUD and variable management (Phase 2)

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/api-client'
import type { Environment, EnvironmentVariable, EffectiveVariable } from '../types/api-types'

// --- Query keys ---
const envKeys = {
  list: (orgId: string) => ['environments', orgId] as const,
  detail: (id: string) => ['environments', id] as const,
  variables: (id: string) => ['environments', id, 'variables'] as const,
  workspaces: (id: string) => ['environments', id, 'workspaces'] as const,
  effectiveVars: (wsId: string) => ['workspaces', wsId, 'effective-variables'] as const,
}

// --- Environment CRUD ---

export function useEnvironments(orgId: string) {
  return useQuery({
    queryKey: envKeys.list(orgId),
    queryFn: () => apiClient.get<Environment[]>('/api/environments', { org_id: orgId }),
    enabled: !!orgId,
  })
}

export function useEnvironment(id: string) {
  return useQuery({
    queryKey: envKeys.detail(id),
    queryFn: () => apiClient.get<Environment>(`/api/environments/${id}`),
    enabled: !!id,
  })
}

export function useCreateEnvironment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      name: string
      org_id: string
      description?: string
      color?: string
      is_protected?: boolean
      auto_apply?: boolean
    }) => apiClient.post<Environment>('/api/environments', body),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['environments', vars.org_id] }),
  })
}

export function useUpdateEnvironment(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<Pick<Environment, 'name' | 'description' | 'color' | 'is_protected' | 'auto_apply'>>) =>
      apiClient.patch<Environment>(`/api/environments/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: envKeys.detail(id) })
      qc.invalidateQueries({ queryKey: ['environments'] })
    },
  })
}

export function useDeleteEnvironment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, force = false }: { id: string; force?: boolean }) =>
      apiClient.del(`/api/environments/${id}${force ? '?force=true' : ''}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['environments'] }),
  })
}

// --- Variable management ---

export function useEnvironmentVariables(envId: string) {
  return useQuery({
    queryKey: envKeys.variables(envId),
    queryFn: () => apiClient.get<EnvironmentVariable[]>(`/api/environments/${envId}/variables`),
    enabled: !!envId,
  })
}

export function useSetEnvironmentVariable(envId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      key: string; value: string; is_sensitive?: boolean
      is_hcl?: boolean; category?: string; description?: string
    }) => apiClient.post<EnvironmentVariable>(`/api/environments/${envId}/variables`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: envKeys.variables(envId) }),
  })
}

export function useDeleteEnvironmentVariable(envId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (key: string) => apiClient.del(`/api/environments/${envId}/variables/${key}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: envKeys.variables(envId) }),
  })
}

// --- Workspace linking ---

export function useLinkWorkspaceToEnvironment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ envId, workspaceId }: { envId: string; workspaceId: string }) =>
      apiClient.post(`/api/environments/${envId}/workspaces/${workspaceId}`, {}),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: envKeys.workspaces(vars.envId) })
      qc.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useEffectiveVariables(workspaceId: string) {
  return useQuery({
    queryKey: envKeys.effectiveVars(workspaceId),
    queryFn: () => apiClient.get<EffectiveVariable[]>(`/api/workspaces/${workspaceId}/effective-variables`),
    enabled: !!workspaceId,
  })
}
