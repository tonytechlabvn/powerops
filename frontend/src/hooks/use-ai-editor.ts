// Hook for AI editor operations — streaming generation, explanation, fix, complete, chat.
// All streaming endpoints consume SSE via fetch + ReadableStream (same pattern as use-sse-stream.ts).

import { useState, useCallback, useRef } from 'react'
import { apiClient } from '../services/api-client'

const BASE_URL = import.meta.env.VITE_API_URL || ''

export type AIStreamStatus = 'idle' | 'loading' | 'streaming' | 'done' | 'error'

export interface AIStreamState {
  text: string
  status: AIStreamStatus
  error: string | null
}

// Low-level SSE fetch that calls onChunk for each text delta and onDone on completion
async function fetchSSE(
  url: string,
  body: unknown,
  onChunk: (chunk: string) => void,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE_URL}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    credentials: 'include',
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) throw new Error(`Request failed: ${res.status}`)

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
      if (data === '[DONE]') return
      // Unescape newlines encoded by SSE response helper
      onChunk(data.replace(/\\n/g, '\n'))
    }
  }
}

export function useAIEditor(workspaceId: string) {
  const [state, setState] = useState<AIStreamState>({ text: '', status: 'idle', error: null })
  const abortRef = useRef<AbortController | null>(null)

  const _startStream = useCallback(
    async (path: string, body: unknown) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setState({ text: '', status: 'loading', error: null })

      try {
        setState(s => ({ ...s, status: 'streaming' }))
        await fetchSSE(
          `/api/workspaces/${workspaceId}${path}`,
          body,
          chunk => setState(s => ({ ...s, text: s.text + chunk })),
          controller.signal,
        )
        setState(s => ({ ...s, status: 'done' }))
      } catch (err) {
        if (controller.signal.aborted) return
        setState(s => ({
          ...s,
          status: 'error',
          error: err instanceof Error ? err.message : 'Stream failed',
        }))
      }
    },
    [workspaceId],
  )

  const generate = useCallback(
    (prompt: string, currentFile?: string, currentContent?: string, provider = 'aws') =>
      _startStream('/ai/generate', { prompt, current_file: currentFile, current_content: currentContent, provider }),
    [_startStream],
  )

  const explain = useCallback(
    (code: string, filePath?: string) =>
      _startStream('/ai/explain', { code, file_path: filePath }),
    [_startStream],
  )

  const suggestFix = useCallback(
    (code: string, error: string, filePath?: string) =>
      _startStream('/ai/fix', { code, error, file_path: filePath }),
    [_startStream],
  )

  const complete = useCallback(
    async (code: string, cursorLine: number, cursorCol: number, filePath?: string): Promise<string> => {
      try {
        const res = await apiClient.post<{ suggestion: string; confidence: number }>(
          `/api/workspaces/${workspaceId}/ai/complete`,
          { code, cursor_line: cursorLine, cursor_col: cursorCol, file_path: filePath },
        )
        return res.suggestion
      } catch {
        return ''
      }
    },
    [workspaceId],
  )

  const chat = useCallback(
    (messages: Array<{ role: string; content: string }>, currentFile?: string, currentContent?: string) =>
      _startStream('/ai/chat', { messages, current_file: currentFile, current_content: currentContent }),
    [_startStream],
  )

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState({ text: '', status: 'idle', error: null })
  }, [])

  return { state, generate, explain, suggestFix, complete, chat, reset }
}
