// React Query hooks for VCS workflow configuration and PR plan runs (Phase 4)

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/api-client'
import type { VCSWorkflowConfig, VCSPlanRun, TriggerPattern } from '../types/api-types'

// --- Query keys ---
const vcsWorkflowKeys = {
  config: (workspaceId: string) => ['vcs-workflow', workspaceId, 'config'] as const,
  prPlans: (workspaceId: string) => ['vcs-workflow', workspaceId, 'pr-plans'] as const,
  prPlan: (workspaceId: string, prNumber: number) =>
    ['vcs-workflow', workspaceId, 'pr-plans', prNumber] as const,
}

// --- Config hooks ---

export function useVCSWorkflowConfig(workspaceId: string) {
  return useQuery({
    queryKey: vcsWorkflowKeys.config(workspaceId),
    queryFn: () =>
      apiClient.get<VCSWorkflowConfig>(`/api/workspaces/${workspaceId}/vcs-workflow`),
    enabled: !!workspaceId,
  })
}

export function useUpdateVCSWorkflowConfig(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { trigger_patterns: TriggerPattern[]; auto_apply?: boolean }) =>
      apiClient.patch<VCSWorkflowConfig>(`/api/workspaces/${workspaceId}/vcs-workflow`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: vcsWorkflowKeys.config(workspaceId) }),
  })
}

// --- PR plan run hooks ---

export function useVCSPRPlans(workspaceId: string) {
  return useQuery({
    queryKey: vcsWorkflowKeys.prPlans(workspaceId),
    queryFn: () =>
      apiClient.get<VCSPlanRun[]>(`/api/workspaces/${workspaceId}/vcs-workflow/pr-plans`),
    enabled: !!workspaceId,
    refetchInterval: 10_000,
  })
}

export function useVCSPRPlanDetail(workspaceId: string, prNumber: number) {
  return useQuery({
    queryKey: vcsWorkflowKeys.prPlan(workspaceId, prNumber),
    queryFn: () =>
      apiClient.get<VCSPlanRun[]>(
        `/api/workspaces/${workspaceId}/vcs-workflow/pr-plans/${prNumber}`
      ),
    enabled: !!workspaceId && prNumber > 0,
    refetchInterval: 5_000,
  })
}

export function useManualReplan(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ prNumber, commitSha }: { prNumber: number; commitSha?: string }) =>
      apiClient.post<{ run_id: string; status: string; commit_sha: string }>(
        `/api/workspaces/${workspaceId}/vcs-workflow/pr-plans/${prNumber}/replan`,
        commitSha ? { commit_sha: commitSha } : {}
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: vcsWorkflowKeys.prPlans(workspaceId) }),
  })
}
