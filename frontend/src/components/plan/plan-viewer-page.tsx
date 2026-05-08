// Plan viewer page: shows plan output for a job and allows approve/reject

import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ChevronLeft, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { useJob, useApprovals, useApprovalDecision } from '../../hooks/use-api'
import { PlanDiffDisplay } from './plan-diff-display'
import { formatDate } from '../../lib/utils'
import { Card, CardHeader, CardBody } from '../_design-system/card'
import { Button } from '../_design-system/button'

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
      <div className="flex items-start gap-3">
        <Link to="/jobs" className="text-zinc-500 hover:text-zinc-200 mt-1">
          <ChevronLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Plan Review</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Job <span className="font-mono text-zinc-500">{job.id.slice(0, 8)}…</span> · {job.workspace} · {formatDate(job.created_at)}
          </p>
        </div>
      </div>

      {/* Plan diff */}
      <Card>
        <CardHeader title="Plan Summary" />
        <CardBody>
          {approval?.plan_summary
            ? <PlanDiffDisplay planSummary={approval.plan_summary} />
            : <p className="text-sm text-zinc-500">No plan summary available.</p>}
        </CardBody>
      </Card>

      {/* Raw output */}
      {job.output && (
        <Card className="bg-zinc-950">
          <CardBody>
            <p className="text-[10px] text-zinc-500 mb-2 uppercase tracking-wider font-medium">Raw Output</p>
            <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap overflow-x-auto max-h-64">
              {job.output}
            </pre>
          </CardBody>
        </Card>
      )}

      {/* Approval decision */}
      {approval && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader title={<span className="text-amber-400">Approval Required</span>} />
          <CardBody className="space-y-4">
            <textarea
              placeholder="Optional reason / comment…"
              value={reason}
              onChange={e => setReason(e.target.value)}
              rows={2}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
            />
            {actionError && (
              <p className="text-sm text-red-400">{actionError}</p>
            )}
            <div className="flex gap-3">
              <Button intent="success" onClick={() => decide(true)} disabled={approvalDecision.isPending}>
                {approvalDecision.isPending ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                Approve
              </Button>
              <Button intent="danger" onClick={() => decide(false)} disabled={approvalDecision.isPending}>
                {approvalDecision.isPending ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
                Reject
              </Button>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
