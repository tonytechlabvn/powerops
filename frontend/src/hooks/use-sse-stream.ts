// SSE streaming hook using fetch + ReadableStream (more reliable than EventSource
// across Cloudflare Tunnel, proxies, and HTTP/2 connections)

import { useState, useEffect, useRef } from 'react'

export type StreamStatus = 'connecting' | 'streaming' | 'completed' | 'error' | 'idle'

export interface SSEStreamState {
  lines: string[]
  status: StreamStatus
  error: string | null
}

const BASE_URL = import.meta.env.VITE_API_URL || ''

// Parse SSE text chunk into individual events
function parseSSEEvents(text: string): Array<{ event?: string; data?: string }> {
  const events: Array<{ event?: string; data?: string }> = []
  const blocks = text.split('\n\n')
  for (const block of blocks) {
    if (!block.trim()) continue
    let event: string | undefined
    let data: string | undefined
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7)
      else if (line.startsWith('data: ')) data = line.slice(6)
    }
    if (data !== undefined) events.push({ event, data })
  }
  return events
}

export function useSSEStream(jobId: string | null): SSEStreamState {
  const [lines, setLines] = useState<string[]>([])
  const [status, setStatus] = useState<StreamStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!jobId) {
      setLines([])
      setStatus('idle')
      setError(null)
      return
    }

    setLines([])
    setError(null)

    const controller = new AbortController()
    abortRef.current = controller

    async function streamFetch() {
      setStatus('connecting')
      try {
        const res = await fetch(`${BASE_URL}/api/stream/${jobId}`, {
          signal: controller.signal,
          headers: { 'Accept': 'text/event-stream' },
        })

        if (!res.ok || !res.body) {
          setStatus('error')
          setError(`Stream request failed: ${res.status}`)
          return
        }

        setStatus('streaming')
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Process complete SSE events (separated by double newline)
          const lastDoubleNewline = buffer.lastIndexOf('\n\n')
          if (lastDoubleNewline === -1) continue

          const complete = buffer.slice(0, lastDoubleNewline + 2)
          buffer = buffer.slice(lastDoubleNewline + 2)

          const events = parseSSEEvents(complete)
          for (const evt of events) {
            if (evt.event === 'log' && evt.data) {
              setLines(prev => [...prev, evt.data!])
            } else if (evt.event === 'result') {
              setStatus('completed')
              reader.cancel()
              return
            } else if (evt.event === 'error' && evt.data) {
              setLines(prev => [...prev, `[error] ${evt.data}`])
              setStatus('error')
              setError(evt.data!)
              reader.cancel()
              return
            }
            // ignore 'ping' keepalive events
          }
        }

        // Stream ended normally
        setStatus('completed')
      } catch (err) {
        if (controller.signal.aborted) return // cleanup, not an error
        setStatus('error')
        setError(err instanceof Error ? err.message : 'Stream connection failed')
      }
    }

    streamFetch()

    return () => {
      controller.abort()
      abortRef.current = null
    }
  }, [jobId])

  return { lines, status, error }
}
