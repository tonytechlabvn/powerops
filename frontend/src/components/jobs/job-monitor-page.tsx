// Job monitor page: history table + per-job detail with live output stream

import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ChevronLeft, Loader2, Trash2, EyeOff } from 'lucide-react'
import { useJobs, useJob, useDestroyMutation, useHideJobMutation } from '../../hooks/use-api'
import { JobOutputStream } from './job-output-stream'
import { JobHistoryTable } from './job-history-table'
import { JobOutputSummary } from './job-output-summary'
import { formatDate } from '../../lib/utils'
import type { Job } from '../../types/api-types'
import { Badge, type BadgeProps } from '../_design-system/badge'
import { Button } from '../_design-system/button'
import { Card, CardHeader, CardBody } from '../_design-system/card'

const jobStatusIntent: Record<Job['status'], NonNullable<BadgeProps['intent']>> = {
  running: 'primary',
  completed: 'success',
  failed: 'danger',
  pending: 'warning',
  cancelled: 'neutral',
}

// --- Individual job detail view ---
function JobDetailView({ id }: { id: string }) {
  const { data: job, isLoading, error } = useJob(id)
  const { data: allJobs } = useJobs()
  const isLive = job?.status === 'running' || job?.status === 'pending'
  const navigate = useNavigate()
  const destroyMutation = useDestroyMutation()
  const hideMutation = useHideJobMutation()
  const [showDestroyConfirm, setShowDestroyConfirm] = useState(false)

  const isTerminal = ['completed', 'failed', 'cancelled'].includes(job?.status ?? '')
  const canHide = isTerminal && !job?.is_hidden

  // Show destroy option only for completed apply jobs with no existing destroy job
  const alreadyDestroyed = (allJobs ?? []).some(
    j => j.type === 'destroy' && j.status !== 'failed' && j.status !== 'cancelled' && j.workspace === job?.workspace
  )
  const canDestroy = job?.status === 'completed' && job?.type === 'apply' && !alreadyDestroyed

  function handleDestroy() {
    if (!job) return
    destroyMutation.mutate(job.workspace, {
      onSuccess: (data) => {
        setShowDestroyConfirm(false)
        navigate(`/jobs/${data.job_id}`)
      },
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-zinc-500 py-8">
        <Loader2 size={16} className="animate-spin" /> Loading job…
      </div>
    )
  }

  if (error || !job) {
    return <div className="text-red-400 py-8">Job not found.</div>
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link to="/jobs" className="text-zinc-500 hover:text-zinc-200 mt-1">
          <ChevronLeft size={20} />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold text-zinc-100 truncate tracking-tight">{job.workspace}</h1>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <Badge intent={jobStatusIntent[job.status] ?? 'neutral'}>{job.status}</Badge>
            <span className="text-xs text-zinc-400 capitalize">{job.type}</span>
            <span className="text-xs text-zinc-600 font-mono">{job.id.slice(0, 12)}…</span>
            <span className="text-xs text-zinc-500">{formatDate(job.created_at)}</span>
          </div>
        </div>
        {canHide && (
          <Button
            intent="secondary"
            size="sm"
            onClick={() => hideMutation.mutate(job!.id, { onSuccess: () => navigate('/jobs') })}
            disabled={hideMutation.isPending}
          >
            {hideMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <EyeOff size={14} />}
            Hide
          </Button>
        )}
        {canDestroy && (
          <Button intent="danger" size="sm" onClick={() => setShowDestroyConfirm(true)}>
            <Trash2 size={14} />
            Destroy
          </Button>
        )}
      </div>

      {/* Destroy confirmation */}
      {showDestroyConfirm && (
        <Card className="border-red-500/30 bg-red-500/5">
          <CardBody className="space-y-3">
            <p className="text-sm text-red-300 font-medium">
              Are you sure you want to destroy all resources in <span className="font-mono">{job.workspace}</span>?
            </p>
            <p className="text-xs text-zinc-400">
              This will permanently destroy all infrastructure managed by this workspace. This action cannot be undone.
            </p>
            {destroyMutation.isError && (
              <p className="text-xs text-red-400">
                Error: {(destroyMutation.error as Error)?.message ?? 'Failed to start destroy'}
              </p>
            )}
            <div className="flex items-center gap-2">
              <Button intent="danger" size="sm" onClick={handleDestroy} disabled={destroyMutation.isPending}>
                {destroyMutation.isPending && <Loader2 size={12} className="animate-spin" />}
                Confirm Destroy
              </Button>
              <Button intent="secondary" size="sm" onClick={() => setShowDestroyConfirm(false)} disabled={destroyMutation.isPending}>
                Cancel
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Live stream for active jobs */}
      {isLive && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-300 mb-3">Live Output</h2>
          <JobOutputStream jobId={job.id} />
        </div>
      )}

      {/* Deployment result summary (outputs, IPs, etc.) */}
      {!isLive && <JobOutputSummary job={job} />}

      {/* Static output for completed jobs */}
      {!isLive && job.output && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-300 mb-3">Output</h2>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4 overflow-x-auto max-h-80 overflow-y-auto">
            <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap">{job.output}</pre>
          </div>
        </div>
      )}

      {/* Error output */}
      {job.error && (
        <div>
          <h2 className="text-sm font-semibold text-red-400 mb-3">Error</h2>
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 overflow-x-auto">
            <pre className="text-xs font-mono text-red-300 whitespace-pre-wrap">{job.error}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Jobs list page ---
function JobListView() {
  const [showHidden, setShowHidden] = useState(false)
  const { data: jobs, isLoading } = useJobs(undefined, showHidden)
  const total = (jobs ?? []).length
  const running = (jobs ?? []).filter(j => j.status === 'running').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Jobs</h1>
          <p className="text-sm text-zinc-400 mt-1">Terraform job history and live monitoring</p>
        </div>
        <div className="flex items-center gap-3">
          {running > 0 && (
            <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-emerald-400 bg-emerald-500/10 ring-1 ring-inset ring-emerald-500/20 px-2 py-0.5 rounded">
              {running} LIVE
            </span>
          )}
          <label className="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showHidden}
              onChange={(e) => setShowHidden(e.target.checked)}
              className="rounded border-zinc-700 bg-zinc-800 text-blue-500 focus:ring-blue-500/30"
            />
            Show hidden
          </label>
          {isLoading && <Loader2 size={16} className="animate-spin text-zinc-500" />}
        </div>
      </div>

      <Card>
        <CardHeader
          title="Job History"
          subtitle={total > 0 ? `${total} total ${showHidden ? '(incl. hidden)' : ''}` : undefined}
        />
        <CardBody className="p-0">
          <JobHistoryTable jobs={jobs ?? []} />
        </CardBody>
      </Card>
    </div>
  )
}

// --- Page entry point ---
export function JobMonitorPage() {
  const { id } = useParams<{ id?: string }>()
  return id ? <JobDetailView id={id} /> : <JobListView />
}
