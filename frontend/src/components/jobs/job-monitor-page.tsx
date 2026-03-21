// Job monitor page: history table + per-job detail with live output stream

import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ChevronLeft, Loader2, Trash2 } from 'lucide-react'
import { useJobs, useJob, useDestroyMutation } from '../../hooks/use-api'
import { JobOutputStream } from './job-output-stream'
import { JobHistoryTable } from './job-history-table'
import { JobOutputSummary } from './job-output-summary'
import { statusColor, formatDate } from '../../lib/utils'

// --- Individual job detail view ---
function JobDetailView({ id }: { id: string }) {
  const { data: job, isLoading, error } = useJob(id)
  const isLive = job?.status === 'running' || job?.status === 'pending'
  const navigate = useNavigate()
  const destroyMutation = useDestroyMutation()
  const [showDestroyConfirm, setShowDestroyConfirm] = useState(false)

  // Show destroy option for completed apply jobs (infrastructure exists)
  const canDestroy = job?.status === 'completed' && job?.type === 'apply'

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
      <div className="flex items-center gap-3">
        <Link to="/jobs" className="text-zinc-500 hover:text-zinc-300">
          <ChevronLeft size={20} />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-zinc-100 truncate">{job.workspace}</h1>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            <span className={`text-xs px-2 py-0.5 rounded border ${statusColor(job.status)}`}>
              {job.status}
            </span>
            <span className="text-xs text-zinc-500 capitalize">{job.type}</span>
            <span className="text-xs text-zinc-600 font-mono">{job.id.slice(0, 12)}…</span>
            <span className="text-xs text-zinc-500">{formatDate(job.created_at)}</span>
          </div>
        </div>
        {canDestroy && (
          <button
            onClick={() => setShowDestroyConfirm(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-300 transition-colors"
          >
            <Trash2 size={14} />
            Destroy
          </button>
        )}
      </div>

      {/* Destroy confirmation */}
      {showDestroyConfirm && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 space-y-3">
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
            <button
              onClick={handleDestroy}
              disabled={destroyMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors"
            >
              {destroyMutation.isPending && <Loader2 size={12} className="animate-spin" />}
              Confirm Destroy
            </button>
            <button
              onClick={() => setShowDestroyConfirm(false)}
              disabled={destroyMutation.isPending}
              className="px-3 py-1.5 text-xs font-medium rounded border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-500 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
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
  const { data: jobs, isLoading } = useJobs()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Jobs</h1>
          <p className="text-sm text-zinc-500 mt-1">Terraform job history and live monitoring</p>
        </div>
        {isLoading && <Loader2 size={16} className="animate-spin text-zinc-500" />}
      </div>

      <JobHistoryTable jobs={jobs ?? []} />
    </div>
  )
}

// --- Page entry point ---
export function JobMonitorPage() {
  const { id } = useParams<{ id?: string }>()
  return id ? <JobDetailView id={id} /> : <JobListView />
}
