// Approvals panel: list pending approvals, review plan summary, approve or reject

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, CheckCircle, XCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { useApprovals, useApprovalDecision } from '../../hooks/use-api'
import { PlanDiffDisplay } from '../plan/plan-diff-display'
import { approvalStatusColor, formatDate } from '../../lib/utils'
import type { Approval } from '../../types/api-types'

interface ApprovalRowProps {
  approval: Approval
}

function ApprovalRow({ approval }: ApprovalRowProps) {
  const [expanded, setExpanded] = useState(false)
  const [reason, setReason] = useState('')
  const [rowError, setRowError] = useState<string | null>(null)
  const decisionMutation = useApprovalDecision()

  const isPending = approval.status === 'pending'

  async function decide(approved: boolean) {
    setRowError(null)
    try {
      await decisionMutation.mutateAsync({ id: approval.id, approved, reason: reason || undefined })
    } catch (err) {
      setRowError(err instanceof Error ? err.message : 'Decision failed')
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden">
      {/* Row header */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-zinc-800/50 transition-colors"
        onClick={() => setExpanded(v => !v)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-zinc-500">
            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Link
                to={`/jobs/${approval.job_id}`}
                className="text-sm font-medium text-zinc-200 hover:text-white font-mono"
                onClick={e => e.stopPropagation()}
              >
                Job {approval.job_id.slice(0, 8)}…
              </Link>
              <span className={`text-xs px-1.5 py-0.5 rounded border ${approvalStatusColor(approval.status)}`}>
                {approval.status}
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">{formatDate(approval.created_at)}</p>
          </div>
        </div>

        {/* Summary counts */}
        {approval.plan_summary && (
          <div className="hidden sm:flex items-center gap-3 text-xs shrink-0">
            <span className="text-green-400">+{approval.plan_summary.adds}</span>
            <span className="text-yellow-400">~{approval.plan_summary.changes}</span>
            <span className="text-red-400">-{approval.plan_summary.destroys}</span>
          </div>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-zinc-800 px-5 py-5 space-y-5">
          {approval.plan_summary ? (
            <PlanDiffDisplay planSummary={approval.plan_summary} />
          ) : (
            <p className="text-sm text-zinc-500">No plan summary available.</p>
          )}

          {approval.reason && !isPending && (
            <p className="text-sm text-zinc-400">
              Reason: <span className="text-zinc-200">{approval.reason}</span>
            </p>
          )}

          {/* Decision controls (only for pending) */}
          {isPending && (
            <div className="space-y-3 pt-2 border-t border-zinc-800">
              <textarea
                placeholder="Optional reason…"
                value={reason}
                onChange={e => setReason(e.target.value)}
                rows={2}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600 resize-none"
                onClick={e => e.stopPropagation()}
              />
              {rowError && <p className="text-sm text-red-400">{rowError}</p>}
              <div className="flex gap-3">
                <button
                  onClick={e => { e.stopPropagation(); decide(true) }}
                  disabled={decisionMutation.isPending}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
                >
                  {decisionMutation.isPending
                    ? <Loader2 size={14} className="animate-spin" />
                    : <CheckCircle size={14} />}
                  Approve
                </button>
                <button
                  onClick={e => { e.stopPropagation(); decide(false) }}
                  disabled={decisionMutation.isPending}
                  className="flex items-center gap-2 bg-red-600 hover:bg-red-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
                >
                  {decisionMutation.isPending
                    ? <Loader2 size={14} className="animate-spin" />
                    : <XCircle size={14} />}
                  Reject
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ApprovalPanelPage() {
  const { data: approvals, isLoading, error } = useApprovals()
  const pending = (approvals ?? []).filter(a => a.status === 'pending')
  const decided = (approvals ?? []).filter(a => a.status !== 'pending')

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Approvals</h1>
          <p className="text-sm text-zinc-500 mt-1">Review and approve Terraform apply plans</p>
        </div>
        {isLoading && <Loader2 size={16} className="animate-spin text-zinc-500" />}
      </div>

      {error && (
        <p className="text-red-400 text-sm">
          Failed to load approvals: {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      )}

      {/* Pending section */}
      {pending.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider">
            Pending ({pending.length})
          </h2>
          {pending.map(a => <ApprovalRow key={a.id} approval={a} />)}
        </div>
      )}

      {/* Decided section */}
      {decided.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
            History ({decided.length})
          </h2>
          {decided.map(a => <ApprovalRow key={a.id} approval={a} />)}
        </div>
      )}

      {!isLoading && (approvals ?? []).length === 0 && !error && (
        <p className="text-sm text-zinc-500">No approvals yet.</p>
      )}
    </div>
  )
}
