// React Query hooks for the Stack Composition & Template API

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/api-client'
import type {
  StackTemplate,
  StackDefinition,
  ComposeResult,
  UpgradeInfo,
} from '../types/api-types'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const stackKeys = {
  templates: () => ['stack-templates'] as const,
  template: (id: string) => ['stack-template', id] as const,
  upgrades: (projectId: string) => ['project-upgrades', projectId] as const,
}

// ---------------------------------------------------------------------------
// Read hooks
// ---------------------------------------------------------------------------

export function useStackTemplates() {
  return useQuery({
    queryKey: stackKeys.templates(),
    queryFn: () => apiClient.get<StackTemplate[]>('/api/stack-templates'),
  })
}

export function useStackTemplate(id: string) {
  return useQuery({
    queryKey: stackKeys.template(id),
    queryFn: () => apiClient.get<StackTemplate>(`/api/stack-templates/${id}`),
    enabled: !!id,
  })
}

export function useModuleUpgrades(projectId: string) {
  return useQuery({
    queryKey: stackKeys.upgrades(projectId),
    queryFn: () => apiClient.get<UpgradeInfo[]>(`/api/projects/${projectId}/upgrades`),
    enabled: !!projectId,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useCreateStackTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; description: string; definition: StackDefinition; tags: string[] }) =>
      apiClient.post<StackTemplate>('/api/stack-templates', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: stackKeys.templates() }),
  })
}

export function useUpdateStackTemplate(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name?: string; description?: string; definition?: StackDefinition; tags?: string[] }) =>
      apiClient.patch<StackTemplate>(`/api/stack-templates/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: stackKeys.templates() })
      qc.invalidateQueries({ queryKey: stackKeys.template(id) })
    },
  })
}

export function useDeleteStackTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.del<void>(`/api/stack-templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: stackKeys.templates() }),
  })
}

export function useComposeProject() {
  return useMutation({
    mutationFn: (body: { project_id: string; stack_definition: StackDefinition; registry_url?: string }) =>
      apiClient.post<ComposeResult>('/api/stacks/compose', body),
  })
}

export function useCreateProjectFromTemplate(templateId: string) {
  return useMutation({
    mutationFn: (body: { project_name: string; variable_overrides?: Record<string, string> }) =>
      apiClient.post<ComposeResult>(`/api/stack-templates/${templateId}/create`, body),
  })
}
