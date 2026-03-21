// Plan viewer page: shows plan output for a job and allows approve/reject

import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ChevronLeft, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { useJob, useApprovals, useApprovalDecision } from '../../hooks/use-api'
import { PlanDiffDisplay } from './plan-diff-display'
import { formatDate } from '../../lib/utils'

export function PlanViewerPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [reason, setReason] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  const { data: job, isLoading: jobLoading } = useJob(id ?? '')
  const { data: approvals } = useApprovals()
  const approvalDecision = useApprovalDecision()

  // Find the approval associated with this job
  const approval = approvals?.find(a => a.job_id === id && a.status === 'pending')

  async function decide(approved: boolean) {
    if (!approval) return
    setActionError(null)
    try {
      await approvalDecision.mutateAsync({ id: approval.id, approved, reason: reason || undefined })
      navigate('/approvals')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Decision failed')
    }
  }

  if (jobLoading) {
    return (
      <div className="flex items-center gap-2 text-zinc-500 py-8">
        <Loader2 size={16} className="animate-spin" /> Loading plan…
      </div>
    )
  }

  if (!job) {
    return <div className="text-red-400 py-8">Job not found.</div>
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back + title */}
      <div className="flex items-center gap-3">
        <Link to="/jobs" className="text-zinc-500 hover:text-zinc-300">
          <ChevronLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Plan Review</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Job <span className="font-mono">{job.id.slice(0, 8)}…</span> &middot; {job.workspace} &middot; {formatDate(job.created_at)}
          </p>
        </div>
      </div>

      {/* Plan diff */}
      {approval?.plan_summary ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-300">Plan Summary</h2>
          <PlanDiffDisplay planSummary={approval.plan_summary} />
        </div>
      ) : (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
          <p className="text-sm text-zinc-500">No plan summary available.</p>
        </div>
      )}

      {/* Raw output */}
      {job.output && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
          <p className="text-xs text-zinc-500 mb-2 uppercase tracking-wider">Raw Output</p>
          <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap overflow-x-auto max-h-64">
            {job.output}
          </pre>
        </div>
      )}

      {/* Approval decision */}
      {approval && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-yellow-400">Approval Required</h2>
          <textarea
            placeholder="Optional reason / comment…"
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={2}
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600 resize-none"
          />
          {actionError && (
            <p className="text-sm text-red-400">{actionError}</p>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => decide(true)}
              disabled={approvalDecision.isPending}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
            >
              {approvalDecision.isPending ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
              Approve
            </button>
            <button
              onClick={() => decide(false)}
              disabled={approvalDecision.isPending}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
            >
              {approvalDecision.isPending ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
