// Card showing plan result for a specific PR (Phase 4)
// Displays: status badge, resource change summary, policy result, link to full output

import { useState } from 'react'
import { CheckCircle2, XCircle, Clock, Loader2, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { VCSPlanRun } from '../../types/api-types'

interface PRPlanStatusCardProps {
  run: VCSPlanRun
  poweropsBaseUrl?: string
}

type RunStatus = 'completed' | 'failed' | 'running' | 'cancelled' | 'pending'

const STATUS_CONFIG: Record<RunStatus, { label: string; icon: React.ReactNode; cardCls: string; badgeCls: string }> = {
  completed: {
    label: 'Plan Passed',
    icon: <CheckCircle2 size={16} className="text-green-400" />,
    cardCls: 'border-green-800/40 bg-green-950/20',
    badgeCls: 'text-green-400 bg-green-900/30 border-green-800/50',
  },
  failed: {
    label: 'Plan Failed',
    icon: <XCircle size={16} className="text-red-400" />,
    cardCls: 'border-red-800/40 bg-red-950/20',
    badgeCls: 'text-red-400 bg-red-900/30 border-red-800/50',
  },
  running: {
    label: 'Running',
    icon: <Loader2 size={16} className="animate-spin text-blue-400" />,
    cardCls: 'border-blue-800/40 bg-blue-950/10',
    badgeCls: 'text-blue-400 bg-blue-900/30 border-blue-800/50',
  },
  cancelled: {
    label: 'Cancelled',
    icon: <XCircle size={16} className="text-zinc-500" />,
    cardCls: 'border-zinc-800 bg-zinc-900/50',
    badgeCls: 'text-zinc-500 bg-zinc-800 border-zinc-700',
  },
  pending: {
    label: 'Pending',
    icon: <Clock size={16} className="text-amber-400" />,
    cardCls: 'border-amber-800/40 bg-amber-950/10',
    badgeCls: 'text-amber-400 bg-amber-900/30 border-amber-800/50',
  },
}

function ChangeCountPill({ count, symbol, colorCls }: { count: number; symbol: string; colorCls: string }) {
  return (
    <span className={cn('inline-flex items-center gap-0.5 font-mono text-sm font-semibold', colorCls)}>
      {symbol}{count}
    </span>
  )
}

export function PRPlanStatusCard({ run, poweropsBaseUrl = 'https://powerops.example.com' }: PRPlanStatusCardProps) {
  const [showOutput, setShowOutput] = useState(false)
  const status = (run.status as RunStatus) in STATUS_CONFIG ? (run.status as RunStatus) : 'pending'
  const cfg = STATUS_CONFIG[status]

  let summary = { adds: 0, changes: 0, destroys: 0 }
  try { summary = JSON.parse(run.plan_summary_json || '{}') } catch { /* ignore malformed */ }

  const triggeredAt = new Date(run.triggered_at || run.created_at).toLocaleString()
  const completedAt = run.completed_at ? new Date(run.completed_at).toLocaleString() : null
  const workspaceUrl = `${poweropsBaseUrl}/workspaces/${run.workspace_id}`

  return (
    <div className={cn('rounded-lg border p-4 space-y-3', cfg.cardCls)}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {cfg.icon}
          <span className="text-sm font-semibold text-zinc-100">{cfg.label}</span>
          <span className={cn('inline-flex items-center px-1.5 py-0.5 rounded text-xs border', cfg.badgeCls)}>
            PR #{run.pr_number}
          </span>
        </div>
        <a
          href={workspaceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors shrink-0"
        >
          <ExternalLink size={11} />
          View
        </a>
      </div>

      {/* Metadata */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500">
        <span className="font-mono">{run.commit_sha.slice(0, 8)}</span>
        <span>branch: <span className="font-mono text-zinc-400">{run.branch}</span></span>
        <span>triggered: {triggeredAt}</span>
        {completedAt && <span>completed: {completedAt}</span>}
      </div>

      {/* Resource change summary */}
      {status !== 'pending' && status !== 'running' && (
        <div className="flex items-center gap-4 py-2 px-3 rounded-md bg-zinc-950/60 border border-zinc-800">
          <span className="text-xs text-zinc-500 mr-1">Changes:</span>
          <ChangeCountPill count={summary.adds}     symbol="+" colorCls="text-green-400" />
          <ChangeCountPill count={summary.changes}  symbol="~" colorCls="text-amber-400" />
          <ChangeCountPill count={summary.destroys} symbol="-" colorCls="text-red-400"   />
        </div>
      )}

      {/* Policy result */}
      {run.policy_passed !== null && run.policy_passed !== undefined && (
        <div className="flex items-center gap-2 text-xs">
          {run.policy_passed
            ? <><CheckCircle2 size={12} className="text-green-400" /><span className="text-green-400">Policy checks passed</span></>
            : <><XCircle size={12} className="text-red-400" /><span className="text-red-400">Policy checks failed</span></>
          }
        </div>
      )}

      {/* Expandable plan output */}
      {run.plan_output && (
        <div>
          <button
            onClick={() => setShowOutput(v => !v)}
            className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {showOutput ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {showOutput ? 'Hide' : 'Show'} plan output
          </button>
          {showOutput && (
            <pre className="mt-2 p-3 rounded-md bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400 whitespace-pre-wrap overflow-x-auto max-h-64 overflow-y-auto">
              {run.plan_output.slice(0, 4000)}
              {run.plan_output.length > 4000 && '\n...(truncated)'}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
