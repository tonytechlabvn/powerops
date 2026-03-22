// React Query hooks for the Private Module Registry API

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/api-client'
import type {
  RegistryModule,
  RegistryModuleVersion,
  ModuleVersionDetail,
  PublishModuleRequest,
} from '../types/api-types'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const registryKeys = {
  modules: (search?: string, provider?: string) =>
    ['registry', 'modules', search, provider] as const,
  module: (id: string) => ['registry', 'module', id] as const,
  versions: (moduleId: string) => ['registry', 'versions', moduleId] as const,
  version: (moduleId: string, version: string) =>
    ['registry', 'version', moduleId, version] as const,
  docs: (moduleId: string, version?: string) =>
    ['registry', 'docs', moduleId, version] as const,
}

// ---------------------------------------------------------------------------
// Read hooks
// ---------------------------------------------------------------------------

export function useRegistryModules(search?: string, provider?: string) {
  return useQuery({
    queryKey: registryKeys.modules(search, provider),
    queryFn: () => {
      const params: Record<string, string> = {}
      if (search) params.search = search
      if (provider) params.provider = provider
      return apiClient.get<RegistryModule[]>('/api/registry/modules', params)
    },
  })
}

export function useRegistryModule(moduleId: string) {
  return useQuery({
    queryKey: registryKeys.module(moduleId),
    queryFn: () => apiClient.get<RegistryModule>(`/api/registry/modules/${moduleId}`),
    enabled: !!moduleId,
  })
}

export function useModuleVersions(moduleId: string) {
  return useQuery({
    queryKey: registryKeys.versions(moduleId),
    queryFn: () =>
      apiClient.get<RegistryModuleVersion[]>(`/api/registry/modules/${moduleId}/versions`),
    enabled: !!moduleId,
  })
}

export function useModuleVersion(moduleId: string, version: string) {
  return useQuery({
    queryKey: registryKeys.version(moduleId, version),
    queryFn: () =>
      apiClient.get<ModuleVersionDetail>(
        `/api/registry/modules/${moduleId}/versions/${version}`
      ),
    enabled: !!moduleId && !!version,
  })
}

export function useModuleDocs(moduleId: string, version?: string) {
  return useQuery({
    queryKey: registryKeys.docs(moduleId, version),
    queryFn: () => {
      const params = version ? { version } : undefined
      return apiClient.get<ModuleVersionDetail>(
        `/api/registry/modules/${moduleId}/docs`,
        params
      )
    },
    enabled: !!moduleId,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function usePublishModule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PublishModuleRequest) =>
      apiClient.post<RegistryModule>('/api/registry/modules', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['registry', 'modules'] }),
  })
}

export function usePublishVersion(moduleId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ version, file }: { version: string; file: File }) => {
      const form = new FormData()
      form.append('archive', file)
      const res = await fetch(
        `/api/registry/modules/${moduleId}/versions?version=${encodeURIComponent(version)}`,
        {
          method: 'POST',
          body: form,
          credentials: 'include',
        }
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Upload failed')
      }
      return res.json() as Promise<RegistryModuleVersion>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: registryKeys.module(moduleId) })
      qc.invalidateQueries({ queryKey: registryKeys.versions(moduleId) })
    },
  })
}

export function useDeprecateModule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (moduleId: string) =>
      apiClient.del<void>(`/api/registry/modules/${moduleId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['registry', 'modules'] }),
  })
}

export function useUpdateModule(moduleId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { description?: string; tags?: string[] }) =>
      apiClient.patch<RegistryModule>(`/api/registry/modules/${moduleId}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: registryKeys.module(moduleId) }),
  })
}
