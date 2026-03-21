// SSE (Server-Sent Events) hook for streaming Terraform job output

import { useState, useEffect, useRef } from 'react'

export type StreamStatus = 'connecting' | 'streaming' | 'completed' | 'error' | 'idle'

export interface SSEStreamState {
  lines: string[]
  status: StreamStatus
  error: string | null
}

const BASE_URL = import.meta.env.VITE_API_URL || ''
const MAX_RECONNECT_ATTEMPTS = 3
const RECONNECT_DELAY_MS = 2000

export function useSSEStream(jobId: string | null): SSEStreamState {
  const [lines, setLines] = useState<string[]>([])
  const [status, setStatus] = useState<StreamStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const attemptsRef = useRef(0)

  useEffect(() => {
    if (!jobId) {
      setLines([])
      setStatus('idle')
      setError(null)
      return
    }

    setLines([])
    setError(null)
    attemptsRef.current = 0

    function connect() {
      esRef.current?.close()
      setStatus('connecting')

      const es = new EventSource(`${BASE_URL}/api/jobs/${jobId}/stream`)
      esRef.current = es

      es.onopen = () => setStatus('streaming')

      // Log lines from 'log' events
      es.addEventListener('log', (e: MessageEvent) => {
        setLines(prev => [...prev, e.data])
      })

      // Status updates
      es.addEventListener('status', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data) as { status: string }
          if (data.status === 'completed' || data.status === 'failed') {
            setStatus('completed')
            es.close()
          }
        } catch {
          // Ignore malformed status events
        }
      })

      // Final result payload
      es.addEventListener('result', (e: MessageEvent) => {
        setLines(prev => [...prev, `[result] ${e.data}`])
        setStatus('completed')
        es.close()
      })

      // Error from server
      es.addEventListener('error', (e: MessageEvent) => {
        setLines(prev => [...prev, `[error] ${e.data}`])
        setStatus('error')
        setError(e.data)
        es.close()
      })

      // Connection-level error — attempt reconnect
      es.onerror = () => {
        es.close()
        if (attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          attemptsRef.current += 1
          setTimeout(connect, RECONNECT_DELAY_MS)
        } else {
          setStatus('error')
          setError('Connection lost. Max reconnection attempts reached.')
        }
      }
    }

    connect()

    return () => {
      esRef.current?.close()
      esRef.current = null
    }
  }, [jobId])

  return { lines, status, error }
}
