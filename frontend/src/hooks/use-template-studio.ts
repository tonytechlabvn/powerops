// Hook for AI Template Studio — generate, extract, refine, validate, save, load templates.
// Uses apiClient for all JSON endpoints with auth token handling.

import { useState, useCallback, useRef } from 'react'
import { apiClient } from '../services/api-client'
import type { StudioTemplate, StudioValidation, ChatMessage, StudioStatus } from '../types/studio-types'

export interface StudioState {
  template: StudioTemplate | null
  status: StudioStatus
  error: string | null
  chatHistory: ChatMessage[]
}

export function useTemplateStudio() {
  const [state, setState] = useState<StudioState>({
    template: null,
    status: 'idle',
    error: null,
    chatHistory: [],
  })
  const abortRef = useRef<AbortController | null>(null)

  // Generate template from NL description
  const generate = useCallback(
    async (description: string, providers: string[] = ['aws'], complexity = 'standard', additionalContext?: string) => {
      abortRef.current?.abort()
      setState(s => ({ ...s, template: null, status: 'generating', error: null, chatHistory: [] }))

      try {
        const result = await apiClient.post<StudioTemplate>('/api/ai/studio/generate', {
          description,
          providers,
          complexity,
          additional_context: additionalContext,
        })
        setState(s => ({ ...s, template: result, status: 'done', error: null }))
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Generation failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [],
  )

  // Extract template from raw HCL
  const extract = useCallback(
    async (hclCode: string, templateName?: string) => {
      abortRef.current?.abort()
      setState(s => ({ ...s, template: null, status: 'extracting', error: null, chatHistory: [] }))

      try {
        const result = await apiClient.post<StudioTemplate>('/api/ai/studio/extract', {
          hcl_code: hclCode,
          template_name: templateName,
        })
        setState(s => ({ ...s, template: result, status: 'done', error: null }))
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Extraction failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [],
  )

  // Refine template with chat-based instructions
  const refine = useCallback(
    async (templateFiles: Record<string, string>, refinement: string, name = '', providers: string[] = ['aws'], description = '') => {
      setState(s => ({ ...s, status: 'refining', error: null }))

      // Build conversation history for API
      const apiHistory = state.chatHistory.map(m => ({ role: m.role, content: m.content }))

      try {
        const result = await apiClient.post<StudioTemplate>('/api/ai/studio/refine', {
          template_files: templateFiles,
          refinement,
          template_name: name,
          providers,
          description,
          conversation_history: apiHistory.length > 0 ? apiHistory : null,
        })

        // Update chat history with this exchange
        const newHistory: ChatMessage[] = [
          ...state.chatHistory,
          { role: 'user', content: refinement },
          { role: 'assistant', content: `Updated ${Object.keys(result.files).length} files.` },
        ]

        setState(s => ({
          ...s,
          template: result,
          status: 'done',
          error: null,
          chatHistory: newHistory.slice(-20), // Keep last 20 messages
        }))
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Refinement failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [state.chatHistory],
  )

  // Validate template files
  const validate = useCallback(
    async (templateFiles: Record<string, string>): Promise<StudioValidation | null> => {
      try {
        return await apiClient.post<StudioValidation>('/api/ai/studio/validate', {
          template_files: templateFiles,
        })
      } catch {
        return null
      }
    },
    [],
  )

  // Save template to library
  const save = useCallback(
    async (templateName: string, files: Record<string, string>, providers: string[] = ['aws'], overwrite = false, description = '', displayName = '', tags: string[] = []) => {
      setState(s => ({ ...s, status: 'saving', error: null }))
      try {
        const result = await apiClient.post<{ saved_path: string; message: string }>('/api/ai/studio/save', {
          template_name: templateName,
          files,
          providers,
          overwrite,
          description,
          display_name: displayName,
          tags,
        })
        setState(s => ({ ...s, status: 'done' }))
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Save failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [],
  )

  // Load template for re-editing
  const load = useCallback(
    async (name: string) => {
      setState(s => ({ ...s, status: 'generating', error: null }))
      try {
        const result = await apiClient.get<StudioTemplate>(`/api/ai/studio/load/${name}`)
        setState(s => ({ ...s, template: result, status: 'done', error: null }))
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Load failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [],
  )

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState({ template: null, status: 'idle', error: null, chatHistory: [] })
  }, [])

  return { state, generate, extract, refine, validate, save, load, reset }
}
