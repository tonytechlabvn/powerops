// HCL validation error/warning panel displayed below the Monaco editor.
// Clicking an error row notifies the parent to jump to that line.

import { AlertCircle, CheckCircle2, ChevronDown, ChevronUp, XCircle } from 'lucide-react'
import { useState } from 'react'
import { cn } from '../../lib/utils'

interface ValidationError {
  line?: number
  message: string
  severity?: 'error' | 'warning'
}

interface ValidationPanelProps {
  errors: ValidationError[]
  isValid: boolean | null   // null = not yet validated
  onJumpToLine?: (line: number) => void
}

export function ValidationPanel({ errors, isValid, onJumpToLine }: ValidationPanelProps) {
  const [collapsed, setCollapsed] = useState(false)

  const errorCount = errors.filter(e => e.severity !== 'warning').length
  const warnCount  = errors.filter(e => e.severity === 'warning').length

  const panelLabel =
    isValid === null ? 'Validation'
    : isValid        ? 'No errors'
    : `${errorCount} error${errorCount !== 1 ? 's' : ''}${warnCount ? `, ${warnCount} warning${warnCount !== 1 ? 's' : ''}` : ''}`

  const headerColor =
    isValid === null ? 'text-zinc-400'
    : isValid        ? 'text-green-400'
    : 'text-red-400'

  return (
    <div className="border-t border-zinc-800 bg-zinc-950 shrink-0" style={{ maxHeight: collapsed ? 36 : 160 }}>
      {/* Header row */}
      <button
        className="flex items-center gap-2 w-full px-3 py-2 text-xs font-medium hover:bg-zinc-900 transition-colors"
        onClick={() => setCollapsed(c => !c)}
      >
        {isValid === null ? (
          <AlertCircle size={13} className="text-zinc-500" />
        ) : isValid ? (
          <CheckCircle2 size={13} className="text-green-400" />
        ) : (
          <XCircle size={13} className="text-red-400" />
        )}
        <span className={headerColor}>{panelLabel}</span>
        <span className="ml-auto text-zinc-600">
          {collapsed ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>

      {/* Error list */}
      {!collapsed && errors.length > 0 && (
        <div className="overflow-y-auto" style={{ maxHeight: 124 }}>
          {errors.map((e, i) => (
            <div
              key={i}
              className={cn(
                'flex items-start gap-2 px-3 py-1.5 text-xs border-t border-zinc-800/60',
                e.line && onJumpToLine ? 'cursor-pointer hover:bg-zinc-900' : '',
                e.severity === 'warning' ? 'text-yellow-300' : 'text-red-300',
              )}
              onClick={() => e.line && onJumpToLine?.(e.line)}
            >
              {e.severity === 'warning'
                ? <AlertCircle size={12} className="text-yellow-400 mt-0.5 shrink-0" />
                : <XCircle size={12} className="text-red-400 mt-0.5 shrink-0" />
              }
              {e.line && (
                <span className="text-zinc-500 shrink-0">Line {e.line}:</span>
              )}
              <span className="break-all">{e.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Empty valid state */}
      {!collapsed && isValid === true && (
        <div className="px-3 py-1.5 text-xs text-zinc-600 border-t border-zinc-800/60">
          HCL syntax is valid.
        </div>
      )}
    </div>
  )
}
