// Dashboard card showing count and list of currently running jobs

import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useJobs } from '../../hooks/use-api'
import { statusColor, formatRelative } from '../../lib/utils'

export function ActiveJobsCard() {
  const { data: jobs, isLoading } = useJobs('running')
  const runningJobs = jobs ?? []

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Active Jobs</h2>
        {isLoading && <Loader2 size={14} className="animate-spin text-zinc-500" />}
      </div>

      <div className="text-4xl font-bold text-blue-400">{runningJobs.length}</div>

      {runningJobs.length === 0 ? (
        <p className="text-sm text-zinc-500">No jobs running</p>
      ) : (
        <ul className="space-y-2">
          {runningJobs.slice(0, 5).map(job => (
            <li key={job.id}>
              <Link
                to={`/jobs/${job.id}`}
                className="flex items-center justify-between text-xs hover:bg-zinc-800 rounded px-2 py-1.5 -mx-2 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <span className={`px-1.5 py-0.5 rounded border text-xs ${statusColor(job.status)}`}>
                    {job.type}
                  </span>
                  <span className="text-zinc-300 truncate max-w-32">{job.workspace}</span>
                </span>
                <span className="text-zinc-500 shrink-0">{formatRelative(job.created_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Link to="/jobs" className="text-xs text-blue-400 hover:text-blue-300 mt-auto">
        View all jobs →
      </Link>
    </div>
  )
}
