// Popover that appears when the user selects HCL code and clicks "Explain".
// Streams explanation text inline; dismisses on outside click or Escape.

import { useEffect, useRef } from 'react'
import { useAIEditor } from '../../hooks/use-ai-editor'

interface AIExplainPopoverProps {
  workspaceId: string
  selectedCode: string
  filePath?: string
  onClose: () => void
}

export function AIExplainPopover({
  workspaceId,
  selectedCode,
  filePath,
  onClose,
}: AIExplainPopoverProps) {
  const { state, explain } = useAIEditor(workspaceId)
  const containerRef = useRef<HTMLDivElement>(null)

  // Trigger explanation on mount
  useEffect(() => {
    if (selectedCode.trim()) {
      explain(selectedCode, filePath)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Dismiss on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  // Dismiss on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  const isLoading = state.status === 'loading' || (state.status === 'streaming' && !state.text)
  const isStreaming = state.status === 'streaming' && !!state.text

  return (
    <div
      ref={containerRef}
      className="absolute z-40 w-96 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl"
      style={{ maxHeight: '360px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800">
        <span className="text-blue-400 text-xs font-semibold">AI Explanation</span>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="text-zinc-500 text-xs animate-pulse">explaining…</span>
          )}
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-base leading-none"
          >
            ×
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 overflow-y-auto" style={{ maxHeight: '300px' }}>
        {/* Selected code preview */}
        <pre className="text-xs bg-zinc-950 border border-zinc-800 rounded p-2 mb-3
                        text-zinc-400 overflow-x-auto whitespace-pre-wrap max-h-20">
          {selectedCode.length > 200 ? selectedCode.slice(0, 200) + '…' : selectedCode}
        </pre>

        {/* Explanation text */}
        {isLoading && (
          <div className="flex gap-1 items-center">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
        )}

        {state.text && (
          <p className="text-zinc-200 text-xs leading-relaxed whitespace-pre-wrap">
            {state.text}
            {isStreaming && <span className="text-blue-400 animate-pulse">▋</span>}
          </p>
        )}

        {state.status === 'error' && (
          <p className="text-red-400 text-xs">{state.error}</p>
        )}
      </div>
    </div>
  )
}
