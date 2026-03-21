// Terminal-like SSE streaming output display for a running job

import { useEffect, useRef } from 'react'
import { Loader2, Wifi, WifiOff } from 'lucide-react'
import { useSSEStream } from '../../hooks/use-sse-stream'
import type { StreamStatus } from '../../hooks/use-sse-stream'

interface JobOutputStreamProps {
  jobId: string
}

function StatusIndicator({ status }: { status: StreamStatus }) {
  switch (status) {
    case 'connecting':
      return (
        <span className="flex items-center gap-1.5 text-xs text-yellow-400">
          <Loader2 size={12} className="animate-spin" /> Connecting…
        </span>
      )
    case 'streaming':
      return (
        <span className="flex items-center gap-1.5 text-xs text-green-400">
          <Wifi size={12} /> Streaming
        </span>
      )
    case 'completed':
      return <span className="text-xs text-zinc-400">Stream ended</span>
    case 'error':
      return (
        <span className="flex items-center gap-1.5 text-xs text-red-400">
          <WifiOff size={12} /> Connection error
        </span>
      )
    default:
      return null
  }
}

export function JobOutputStream({ jobId }: JobOutputStreamProps) {
  const { lines, status, error } = useSSEStream(jobId)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom as new lines arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div className="rounded-lg border border-zinc-800 overflow-hidden">
      {/* Terminal header bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-800 border-b border-zinc-700">
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500/70" />
          <span className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <span className="w-3 h-3 rounded-full bg-green-500/70" />
        </div>
        <StatusIndicator status={status} />
      </div>

      {/* Output area */}
      <div className="bg-zinc-950 p-4 h-80 overflow-y-auto font-mono text-xs leading-relaxed">
        {lines.length === 0 && status === 'connecting' && (
          <span className="text-zinc-600">Waiting for output…</span>
        )}
        {lines.map((line, i) => (
          <div
            key={i}
            className={[
              line.startsWith('[error]') ? 'text-red-400' :
              line.startsWith('[result]') ? 'text-green-400' :
              'text-zinc-300',
            ].join('')}
          >
            {line}
          </div>
        ))}
        {error && (
          <div className="text-red-400 mt-2 border-t border-zinc-800 pt-2">{error}</div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
