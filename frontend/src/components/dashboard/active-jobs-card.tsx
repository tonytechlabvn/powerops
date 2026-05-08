// Dashboard card showing count and list of currently running jobs.

import { Link } from 'react-router-dom'
import { Loader2, ArrowRight } from 'lucide-react'
import { useJobs } from '../../hooks/use-api'
import { formatRelative } from '../../lib/utils'
import { Card, CardHeader, CardBody } from '../_design-system/card'
import { Badge } from '../_design-system/badge'

export function ActiveJobsCard() {
  const { data: jobs, isLoading } = useJobs('running')
  const runningJobs = jobs ?? []

  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Active Jobs"
        actions={isLoading ? <Loader2 size={14} className="animate-spin text-zinc-500" /> : undefined}
      />
      <CardBody className="flex-1 flex flex-col gap-3">
        <div className="text-3xl font-semibold text-zinc-100">{runningJobs.length}</div>

        {runningJobs.length === 0 ? (
          <p className="text-xs text-zinc-500">No jobs running</p>
        ) : (
          <ul className="space-y-1">
            {runningJobs.slice(0, 5).map(job => (
              <li key={job.id}>
                <Link
                  to={`/jobs/${job.id}`}
                  className="flex items-center justify-between gap-2 px-2 -mx-2 py-1 rounded text-xs hover:bg-zinc-800/60 transition-colors"
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <Badge intent="primary">{job.type}</Badge>
                    <span className="text-zinc-300 truncate">{job.workspace}</span>
                  </span>
                  <span className="text-zinc-500 shrink-0 font-mono">{formatRelative(job.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        <Link
          to="/jobs"
          className="mt-auto inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          View all jobs <ArrowRight size={12} />
        </Link>
      </CardBody>
    </Card>
  )
}
