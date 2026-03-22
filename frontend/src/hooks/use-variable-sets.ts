// Hook for variable set CRUD operations wrapping the variable sets API

import { useState, useCallback } from 'react'
import { apiClient } from '../services/api-client'
import type { VariableSet, VariableSetVariable } from '../types/api-types'

interface UseVariableSetsReturn {
  variableSets: VariableSet[]
  isLoading: boolean
  error: string | null
  listSets: (orgId?: string) => Promise<void>
  getSet: (id: string) => Promise<VariableSet>
  createSet: (name: string, description?: string, isGlobal?: boolean, orgId?: string) => Promise<VariableSet>
  updateSet: (id: string, name?: string, description?: string) => Promise<VariableSet>
  deleteSet: (id: string) => Promise<void>
  setVariable: (vsId: string, variable: Omit<VariableSetVariable, 'id' | 'variable_set_id'>) => Promise<void>
  deleteVariable: (vsId: string, varId: string) => Promise<void>
  assignToWorkspace: (vsId: string, workspaceId: string, priority?: number) => Promise<void>
  unassignFromWorkspace: (vsId: string, workspaceId: string) => Promise<void>
}

export function useVariableSets(): UseVariableSetsReturn {
  const [variableSets, setVariableSets] = useState<VariableSet[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const withLoading = useCallback(async <T>(fn: () => Promise<T>): Promise<T> => {
    setIsLoading(true)
    setError(null)
    try {
      return await fn()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const listSets = useCallback(async (orgId = 'default') => {
    await withLoading(async () => {
      const res = await apiClient.get<{ variable_sets: VariableSet[] }>(
        '/api/variable-sets', { org_id: orgId }
      )
      setVariableSets(res.variable_sets ?? [])
    })
  }, [withLoading])

  const getSet = useCallback(async (id: string): Promise<VariableSet> => {
    return withLoading(() => apiClient.get<VariableSet>(`/api/variable-sets/${id}`))
  }, [withLoading])

  const createSet = useCallback(async (
    name: string, description = '', isGlobal = false, orgId = 'default'
  ): Promise<VariableSet> => {
    return withLoading(async () => {
      const result = await apiClient.post<VariableSet>('/api/variable-sets', {
        name, description, is_global: isGlobal, org_id: orgId,
      })
      setVariableSets(prev => [...prev, result])
      return result
    })
  }, [withLoading])

  const updateSet = useCallback(async (
    id: string, name?: string, description?: string
  ): Promise<VariableSet> => {
    return withLoading(async () => {
      const result = await apiClient.patch<VariableSet>(`/api/variable-sets/${id}`, { name, description })
      setVariableSets(prev => prev.map(s => s.id === id ? result : s))
      return result
    })
  }, [withLoading])

  const deleteSet = useCallback(async (id: string) => {
    await withLoading(async () => {
      await apiClient.del(`/api/variable-sets/${id}`)
      setVariableSets(prev => prev.filter(s => s.id !== id))
    })
  }, [withLoading])

  const setVariable = useCallback(async (
    vsId: string, variable: Omit<VariableSetVariable, 'id' | 'variable_set_id'>
  ) => {
    await withLoading(() =>
      apiClient.post(`/api/variable-sets/${vsId}/variables`, {
        key: variable.key,
        value: variable.value,
        category: variable.category,
        is_sensitive: variable.is_sensitive,
        is_hcl: variable.is_hcl,
        description: variable.description,
      })
    )
  }, [withLoading])

  const deleteVariable = useCallback(async (vsId: string, varId: string) => {
    await withLoading(() => apiClient.del(`/api/variable-sets/${vsId}/variables/${varId}`))
  }, [withLoading])

  const assignToWorkspace = useCallback(async (
    vsId: string, workspaceId: string, priority = 0
  ) => {
    await withLoading(() =>
      apiClient.post(`/api/variable-sets/${vsId}/assign/${workspaceId}`, { priority })
    )
  }, [withLoading])

  const unassignFromWorkspace = useCallback(async (vsId: string, workspaceId: string) => {
    await withLoading(() =>
      apiClient.del(`/api/variable-sets/${vsId}/assign/${workspaceId}`)
    )
  }, [withLoading])

  return {
    variableSets, isLoading, error,
    listSets, getSet, createSet, updateSet, deleteSet,
    setVariable, deleteVariable, assignToWorkspace, unassignFromWorkspace,
  }
}
