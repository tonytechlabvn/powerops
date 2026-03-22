// Panel that appears below validation errors offering AI-suggested HCL fixes.
// Shows streaming fix suggestion with accept/reject actions.

import { useState } from 'react'
import { useAIEditor } from '../../hooks/use-ai-editor'

interface ValidationError {
  message: string
  line?: number
}

interface AIFixSuggestionPanelProps {
  workspaceId: string
  errors: ValidationError[]
  currentCode: string
  filePath?: string
  onApplyFix: (fixedCode: string) => void
}

// Extract HCL from <terraform> tags or return full text
function extractHCL(text: string): string {
  const match = text.match(/<terraform>([\s\S]*?)<\/terraform>/)
  return match ? match[1].trim() : text.trim()
}

export function AIFixSuggestionPanel({
  workspaceId,
  errors,
  currentCode,
  filePath,
  onApplyFix,
}: AIFixSuggestionPanelProps) {
  const [activeErrorIdx, setActiveErrorIdx] = useState<number | null>(null)
  const { state, suggestFix, reset } = useAIEditor(workspaceId)

  const handleRequestFix = (error: ValidationError, idx: number) => {
    setActiveErrorIdx(idx)
    reset()
    suggestFix(currentCode, error.message, filePath)
  }

  const handleApply = () => {
    const hcl = extractHCL(state.text)
    if (hcl) onApplyFix(hcl)
    reset()
    setActiveErrorIdx(null)
  }

  const handleDismiss = () => {
    reset()
    setActiveErrorIdx(null)
  }

  const isStreaming = state.status === 'streaming' || state.status === 'loading'
  const isDone = state.status === 'done' && !!state.text

  if (errors.length === 0) return null

  return (
    <div className="border-t border-zinc-800 bg-zinc-900">
      {/* Error list with AI fix buttons */}
      <div className="px-4 py-2 space-y-1">
        {errors.map((err, idx) => (
          <div key={idx} className="flex items-start justify-between gap-3 py-1">
            <div className="flex items-start gap-2 flex-1 min-w-0">
              <span className="text-red-400 text-xs mt-0.5 shrink-0">✕</span>
              <span className="text-zinc-300 text-xs truncate">
                {err.line != null && (
                  <span className="text-zinc-500 mr-1">Line {err.line}:</span>
                )}
                {err.message}
              </span>
            </div>
            <button
              onClick={() => handleRequestFix(err, idx)}
              disabled={isStreaming}
              className="shrink-0 px-2 py-0.5 text-xs bg-blue-900/50 hover:bg-blue-800/60
                         text-blue-300 border border-blue-700/50 rounded
                         disabled:opacity-40 transition-colors"
            >
              {activeErrorIdx === idx && isStreaming ? 'Fixing…' : 'AI Fix'}
            </button>
          </div>
        ))}
      </div>

      {/* Fix suggestion display */}
      {activeErrorIdx !== null && (isStreaming || isDone) && (
        <div className="mx-4 mb-3 border border-zinc-700 rounded bg-zinc-950">
          <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
            <span className="text-xs text-blue-400 font-medium">
              Suggested Fix
              {isStreaming && <span className="text-zinc-500 animate-pulse ml-2">generating…</span>}
            </span>
            {isDone && (
              <div className="flex gap-2">
                <button
                  onClick={handleApply}
                  className="px-2 py-0.5 text-xs bg-green-700 hover:bg-green-600
                             text-white rounded transition-colors"
                >
                  Apply Fix
                </button>
                <button
                  onClick={handleDismiss}
                  className="px-2 py-0.5 text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
          <pre className="p-3 text-xs text-green-300 overflow-x-auto whitespace-pre-wrap max-h-48">
            {extractHCL(state.text) || state.text}
            {isStreaming && <span className="text-blue-400 animate-pulse">▋</span>}
          </pre>
        </div>
      )}

      {state.status === 'error' && activeErrorIdx !== null && (
        <p className="px-4 pb-2 text-red-400 text-xs">{state.error}</p>
      )}
    </div>
  )
}
