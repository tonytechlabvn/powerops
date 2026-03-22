// Hook for workspace file CRUD operations wrapping the HCL file management API

import { useState, useCallback } from 'react'
import { apiClient } from '../services/api-client'
import type { FileInfo, FileContent, WriteFileResponse, SearchResult } from '../types/api-types'

interface UseWorkspaceFilesReturn {
  files: FileInfo[]
  openFile: FileContent | null
  isLoading: boolean
  error: string | null
  listFiles: (pattern?: string) => Promise<void>
  readFile: (path: string) => Promise<void>
  createFile: (path: string, content: string) => Promise<WriteFileResponse>
  updateFile: (path: string, content: string, expectedChecksum?: string) => Promise<WriteFileResponse>
  deleteFile: (path: string) => Promise<void>
  renameFile: (oldPath: string, newPath: string) => Promise<void>
  createDirectory: (path: string) => Promise<void>
  deleteDirectory: (path: string) => Promise<void>
  searchFiles: (query: string, pattern?: string) => Promise<SearchResult[]>
  validateFile: (path: string, content: string) => Promise<{ valid: boolean; errors: string[] }>
  clearOpenFile: () => void
}

export function useWorkspaceFiles(workspaceId: string): UseWorkspaceFilesReturn {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [openFile, setOpenFile] = useState<FileContent | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const base = `/api/workspaces/${workspaceId}/files`

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

  const listFiles = useCallback(async (pattern = '**/*.tf') => {
    await withLoading(async () => {
      const res = await apiClient.get<{ files: FileInfo[] }>(base, { pattern })
      setFiles(res.files ?? [])
    })
  }, [base, withLoading])

  const readFile = useCallback(async (path: string) => {
    await withLoading(async () => {
      const fc = await apiClient.get<FileContent>(`${base}/${path}`)
      setOpenFile(fc)
    })
  }, [base, withLoading])

  const createFile = useCallback(async (path: string, content: string): Promise<WriteFileResponse> => {
    return withLoading(() =>
      apiClient.post<WriteFileResponse>(`${base}/${path}`, { content })
    )
  }, [base, withLoading])

  const updateFile = useCallback(async (
    path: string,
    content: string,
    expectedChecksum?: string,
  ): Promise<WriteFileResponse> => {
    return withLoading(() =>
      apiClient.put<WriteFileResponse>(`${base}/${path}`, { content, expected_checksum: expectedChecksum })
    )
  }, [base, withLoading])

  const deleteFile = useCallback(async (path: string) => {
    await withLoading(() => apiClient.del(`${base}/${path}`))
    setFiles(prev => prev.filter(f => f.path !== path))
    if (openFile?.path === path) setOpenFile(null)
  }, [base, withLoading, openFile])

  const renameFile = useCallback(async (oldPath: string, newPath: string) => {
    await withLoading(() =>
      apiClient.post(`${base}/${oldPath}/rename`, { new_path: newPath })
    )
  }, [base, withLoading])

  const createDirectory = useCallback(async (path: string) => {
    await withLoading(() =>
      apiClient.post(`/api/workspaces/${workspaceId}/directories`, { path })
    )
  }, [workspaceId, withLoading])

  const deleteDirectory = useCallback(async (path: string) => {
    await withLoading(() =>
      apiClient.del(`/api/workspaces/${workspaceId}/directories/${path}`)
    )
  }, [workspaceId, withLoading])

  const searchFiles = useCallback(async (query: string, pattern = '**/*.tf'): Promise<SearchResult[]> => {
    return withLoading(async () => {
      const res = await apiClient.post<{ results: SearchResult[] }>(`${base}/search`, { query, pattern })
      return res.results ?? []
    })
  }, [base, withLoading])

  const validateFile = useCallback(async (path: string, content: string) => {
    return withLoading(() =>
      apiClient.post<{ valid: boolean; errors: string[] }>(`${base}/${path}/validate`, { content })
    )
  }, [base, withLoading])

  const clearOpenFile = useCallback(() => setOpenFile(null), [])

  return {
    files, openFile, isLoading, error,
    listFiles, readFile, createFile, updateFile, deleteFile,
    renameFile, createDirectory, deleteDirectory,
    searchFiles, validateFile, clearOpenFile,
  }
}
