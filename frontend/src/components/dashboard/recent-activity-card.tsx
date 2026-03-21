// Dashboard card showing last 10 jobs as a timeline

import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useJobs } from '../../hooks/use-api'
import { statusColor, formatRelative } from '../../lib/utils'
import type { Job } from '../../types/api-types'

function StatusDot({ status }: { status: Job['status'] }) {
  const colors: Record<Job['status'], string> = {
    running:   'bg-blue-400',
    completed: 'bg-green-400',
    failed:    'bg-red-400',
    pending:   'bg-yellow-400',
    cancelled: 'bg-zinc-500',
  }
  return (
    <span className={`w-2 h-2 rounded-full shrink-0 mt-1 ${colors[status] ?? 'bg-zinc-500'}`} />
  )
}

export function RecentActivityCard() {
  const { data: jobs, isLoading } = useJobs()
  const recent = (jobs ?? []).slice(0, 10)

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          Recent Activity
        </h2>
        {isLoading && <Loader2 size={14} className="animate-spin text-zinc-500" />}
      </div>

      {recent.length === 0 ? (
        <p className="text-sm text-zinc-500">No recent activity</p>
      ) : (
        <ul className="space-y-3">
          {recent.map(job => (
            <li key={job.id} className="flex items-start gap-3">
              <StatusDot status={job.status} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <Link
                    to={`/jobs/${job.id}`}
                    className="text-xs text-zinc-300 hover:text-white truncate"
                  >
                    {job.workspace}
                  </Link>
                  <span className="text-zinc-600 text-xs shrink-0">
                    {formatRelative(job.created_at)}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${statusColor(job.status)}`}>
                    {job.status}
                  </span>
                  <span className="text-zinc-600 text-xs">{job.type}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Link to="/jobs" className="text-xs text-blue-400 hover:text-blue-300 mt-auto">
        Full job history →
      </Link>
    </div>
  )
}
