// Dashboard card showing count of pending approvals with link.

import { Link } from 'react-router-dom'
import { AlertCircle, Loader2, ArrowRight } from 'lucide-react'
import { useApprovals } from '../../hooks/use-api'
import { formatRelative } from '../../lib/utils'
import { Card, CardHeader, CardBody } from '../_design-system/card'

export function PendingApprovalsCard() {
  const { data: approvals, isLoading } = useApprovals()
  const pending = (approvals ?? []).filter(a => a.status === 'pending')
  const hasPending = pending.length > 0

  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Pending Approvals"
        actions={isLoading ? <Loader2 size={14} className="animate-spin text-zinc-500" /> : undefined}
      />
      <CardBody className="flex-1 flex flex-col gap-3">
        <div className="flex items-end gap-2">
          <span className={`text-3xl font-semibold ${hasPending ? 'text-amber-400' : 'text-zinc-100'}`}>
            {pending.length}
          </span>
          {hasPending && <AlertCircle size={18} className="text-amber-400 mb-1.5" />}
        </div>

        {!hasPending ? (
          <p className="text-xs text-zinc-500">No approvals waiting</p>
        ) : (
          <ul className="space-y-1">
            {pending.slice(0, 5).map(approval => (
              <li key={approval.id} className="flex items-center justify-between gap-2 text-xs">
                <span className="text-zinc-400 font-mono truncate">job {approval.job_id.slice(0, 8)}…</span>
                <span className="text-zinc-500 shrink-0">{formatRelative(approval.created_at)}</span>
              </li>
            ))}
          </ul>
        )}

        <Link
          to="/approvals"
          className="mt-auto inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors"
        >
          Review approvals <ArrowRight size={12} />
        </Link>
      </CardBody>
    </Card>
  )
}
