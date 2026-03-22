// Lab validation result panel showing per-message pass/fail and overall status

import { CheckCircle, XCircle, Loader2 } from 'lucide-react'
import type { LabValidationResult } from '../../types/kb-types'

interface KBValidationResultProps {
  result: LabValidationResult | null
  isLoading: boolean
}

export function KBValidationResult({ result, isLoading }: KBValidationResultProps) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-zinc-400 text-sm p-4">
        <Loader2 size={16} className="animate-spin" /> Validating...
      </div>
    )
  }

  if (!result) {
    return (
      <div className="text-zinc-600 text-sm p-4">
        Run validation to see results here.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Overall status */}
      <div className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
        result.passed ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
      }`}>
        {result.passed
          ? <CheckCircle size={16} />
          : <XCircle size={16} />}
        {result.passed ? 'All checks passed' : 'Some checks failed'}
        <span className="ml-auto text-xs opacity-70">Level: {result.level}</span>
      </div>

      {/* Per-message results */}
      <div className="space-y-2">
        {result.messages.map((msg, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 px-3 py-2 rounded-md text-xs border ${
              msg.passed
                ? 'border-green-800/50 bg-green-900/10 text-green-300'
                : 'border-red-800/50 bg-red-900/10 text-red-300'
            }`}
          >
            {msg.passed
              ? <CheckCircle size={13} className="shrink-0 mt-0.5" />
              : <XCircle size={13} className="shrink-0 mt-0.5" />}
            <span className="flex-1 leading-relaxed">{msg.message}</span>
            {msg.pattern && (
              <code className="shrink-0 text-zinc-500 font-mono">{msg.pattern}</code>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
