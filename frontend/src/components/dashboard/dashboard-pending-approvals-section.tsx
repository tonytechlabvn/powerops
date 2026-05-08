// Pending approvals section for dashboard: inline plan diff + Approve/Reject buttons.
// Stitch-inspired: power-user feature consolidating /approvals essentials onto dashboard.

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, CheckCircle, XCircle, ArrowRight } from 'lucide-react'
import { useApprovals, useApprovalDecision } from '../../hooks/use-api'
import { formatRelative } from '../../lib/utils'
import type { Approval } from '../../types/api-types'
import { Card, CardHeader, CardBody } from '../_design-system/card'
import { Button } from '../_design-system/button'
import { EmptyState } from '../_design-system/empty-state'

function PlanDiffPills({ approval }: { approval: Approval }) {
  const ps = approval.plan_summary
  if (!ps) {
    return <span className="text-xs text-zinc-600">No plan summary</span>
  }
  return (
    <div className="flex items-center gap-3 font-mono text-xs">
      <span className="text-emerald-400">+{ps.adds} <span className="text-zinc-500 font-sans">to add</span></span>
      <span className="text-amber-400">~{ps.changes} <span className="text-zinc-500 font-sans">to change</span></span>
      <span className="text-red-400">-{ps.destroys} <span className="text-zinc-500 font-sans">to destroy</span></span>
    </div>
  )
}

interface ApprovalRowProps {
  approval: Approval
}

function ApprovalRow({ approval }: ApprovalRowProps) {
  const decisionMutation = useApprovalDecision()
  const [error, setError] = useState<string | null>(null)
  const isDestructive = (approval.plan_summary?.destroys ?? 0) > 0

  async function decide(approved: boolean) {
    setError(null)
    try {
      await decisionMutation.mutateAsync({ id: approval.id, approved })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Decision failed')
    }
  }

  return (
    <div className="flex items-center justify-between gap-4 px-6 py-3 hover:bg-zinc-800/40 transition-colors duration-150">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Link
            to={`/jobs/${approval.job_id}/plan`}
            className="text-sm text-zinc-100 hover:text-blue-400 font-mono truncate max-w-[200px]"
          >
            job {approval.job_id.slice(0, 8)}…
          </Link>
          {isDestructive && (
            <span className="inline-flex items-center text-[10px] font-mono uppercase tracking-wider text-red-400 bg-red-500/10 ring-1 ring-inset ring-red-500/20 px-1.5 py-0.5 rounded">
              destroy
            </span>
          )}
          <span className="text-xs text-zinc-500 font-mono">{formatRelative(approval.created_at)}</span>
        </div>
        <div className="mt-1.5">
          <PlanDiffPills approval={approval} />
        </div>
        {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Button
          intent="ghost"
          size="sm"
          onClick={() => decide(false)}
          disabled={decisionMutation.isPending}
        >
          {decisionMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={12} />}
          Reject
        </Button>
        <Button
          intent={isDestructive ? 'danger' : 'success'}
          size="sm"
          onClick={() => decide(true)}
          disabled={decisionMutation.isPending}
        >
          {decisionMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />}
          Approve
        </Button>
      </div>
    </div>
  )
}

export function DashboardPendingApprovalsSection() {
  const { data: approvals, isLoading } = useApprovals()
  const pending = (approvals ?? []).filter(a => a.status === 'pending').slice(0, 5)

  if (isLoading) {
    return null
  }

  return (
    <Card>
      <CardHeader
        title="Pending Approvals"
        subtitle={pending.length > 0 ? `${pending.length} awaiting your decision` : 'All caught up'}
        actions={
          pending.length > 0 ? (
            <Link
              to="/approvals"
              className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors"
            >
              View all <ArrowRight size={12} />
            </Link>
          ) : undefined
        }
      />
      <CardBody className="p-0">
        {pending.length === 0 ? (
          <div className="px-6 py-6">
            <EmptyState
              title="No pending approvals"
              description="When a Terraform plan needs review, it will appear here for quick action."
            />
          </div>
        ) : (
          <div className="divide-y divide-zinc-800">
            {pending.map(a => <ApprovalRow key={a.id} approval={a} />)}
          </div>
        )}
      </CardBody>
    </Card>
  )
}
