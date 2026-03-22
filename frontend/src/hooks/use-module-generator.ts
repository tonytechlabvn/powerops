// Hook for AI module generation — generate, refine, validate, and publish modules.
// Uses apiClient for JSON endpoints and fetch for SSE streaming generation.

import { useState, useCallback, useRef } from 'react'
import { apiClient } from '../services/api-client'
import type { GeneratedModuleResponse, ModuleValidationResponse } from '../types/api-types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

export type GeneratorStatus = 'idle' | 'generating' | 'done' | 'error'

export interface GeneratorState {
  module: GeneratedModuleResponse | null
  status: GeneratorStatus
  error: string | null
  streamText: string   // raw streaming text accumulator for progressive display
}

export interface PublishOptions {
  namespace: string
  name: string
  provider: string
  version: string
  description: string
  tags?: string[]
}

export function useModuleGenerator() {
  const [state, setState] = useState<GeneratorState>({
    module: null,
    status: 'idle',
    error: null,
    streamText: '',
  })
  const abortRef = useRef<AbortController | null>(null)

  // Generate a complete module (non-streaming, awaits full result)
  const generate = useCallback(
    async (description: string, provider = 'aws', complexity = 'standard', additionalContext?: string) => {
      abortRef.current?.abort()
      setState({ module: null, status: 'generating', error: null, streamText: '' })

      try {
        const result = await apiClient.post<GeneratedModuleResponse>('/api/ai/generate-module', {
          description,
          provider,
          complexity,
          additional_context: additionalContext,
        })
        setState({ module: result, status: 'done', error: null, streamText: '' })
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Generation failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [],
  )

  // Stream module generation — updates streamText progressively, then calls generate() for final result
  const generateStreaming = useCallback(
    async (description: string, provider = 'aws', complexity = 'standard') => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setState({ module: null, status: 'generating', error: null, streamText: '' })

      try {
        const res = await fetch(`${BASE_URL}/api/ai/generate-module/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
          credentials: 'include',
          body: JSON.stringify({ description, provider, complexity }),
          signal: controller.signal,
        })

        if (!res.ok || !res.body) throw new Error(`Stream request failed: ${res.status}`)

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const data = line.slice(6)
            if (data === '[DONE]') break
            setState(s => ({ ...s, streamText: s.streamText + data.replace(/\\n/g, '\n') }))
          }
        }

        // After stream completes, fetch structured result
        return await generate(description, provider, complexity)
      } catch (err) {
        if (controller.signal.aborted) return null
        const msg = err instanceof Error ? err.message : 'Stream failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [generate],
  )

  // Refine an existing module with additional instructions
  const refine = useCallback(
    async (moduleFiles: Record<string, string>, refinement: string, name = '', provider = 'aws', description = '') => {
      setState(s => ({ ...s, status: 'generating', error: null }))
      try {
        const result = await apiClient.post<GeneratedModuleResponse>('/api/ai/generate-module/refine', {
          module_files: moduleFiles,
          refinement,
          name,
          provider,
          description,
        })
        setState(s => ({ ...s, module: result, status: 'done' }))
        return result
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Refinement failed'
        setState(s => ({ ...s, status: 'error', error: msg }))
        return null
      }
    },
    [],
  )

  // Validate module files for HCL syntax and structure
  const validate = useCallback(async (moduleFiles: Record<string, string>): Promise<ModuleValidationResponse | null> => {
    try {
      return await apiClient.post<ModuleValidationResponse>('/api/ai/generate-module/validate', {
        module_files: moduleFiles,
      })
    } catch {
      return null
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState({ module: null, status: 'idle', error: null, streamText: '' })
  }, [])

  return { state, generate, generateStreaming, refine, validate, reset }
}
