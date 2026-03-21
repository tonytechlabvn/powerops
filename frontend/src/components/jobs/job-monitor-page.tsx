// Job monitor page: history table + per-job detail with live output stream

import { useParams, Link } from 'react-router-dom'
import { ChevronLeft, Loader2 } from 'lucide-react'
import { useJobs, useJob } from '../../hooks/use-api'
import { JobOutputStream } from './job-output-stream'
import { JobHistoryTable } from './job-history-table'
import { statusColor, formatDate } from '../../lib/utils'

// --- Individual job detail view ---
function JobDetailView({ id }: { id: string }) {
  const { data: job, isLoading, error } = useJob(id)
  const isLive = job?.status === 'running' || job?.status === 'pending'

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
      </div>

      {/* Live stream for active jobs */}
      {isLive && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-300 mb-3">Live Output</h2>
          <JobOutputStream jobId={job.id} />
        </div>
      )}

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
