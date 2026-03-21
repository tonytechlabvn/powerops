// Dashboard card showing count of pending approvals with link

import { Link } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { useApprovals } from '../../hooks/use-api'
import { formatRelative } from '../../lib/utils'

export function PendingApprovalsCard() {
  const { data: approvals, isLoading } = useApprovals()
  const pending = (approvals ?? []).filter(a => a.status === 'pending')

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          Pending Approvals
        </h2>
        {isLoading && <Loader2 size={14} className="animate-spin text-zinc-500" />}
      </div>

      <div className="flex items-end gap-2">
        <span className="text-4xl font-bold text-yellow-400">{pending.length}</span>
        {pending.length > 0 && (
          <AlertCircle size={20} className="text-yellow-400 mb-1" />
        )}
      </div>

      {pending.length === 0 ? (
        <p className="text-sm text-zinc-500">No approvals waiting</p>
      ) : (
        <ul className="space-y-2">
          {pending.slice(0, 5).map(approval => (
            <li key={approval.id} className="text-xs text-zinc-400 flex justify-between">
              <span className="truncate max-w-36">Job {approval.job_id.slice(0, 8)}…</span>
              <span className="text-zinc-500 shrink-0">{formatRelative(approval.created_at)}</span>
            </li>
          ))}
        </ul>
      )}

      <Link to="/approvals" className="text-xs text-yellow-400 hover:text-yellow-300 mt-auto">
        Review approvals →
      </Link>
    </div>
  )
}
