// Dashboard card showing last 10 jobs as a status timeline.

import { Link } from 'react-router-dom'
import { Loader2, ArrowRight } from 'lucide-react'
import { useJobs } from '../../hooks/use-api'
import { formatRelative } from '../../lib/utils'
import type { Job } from '../../types/api-types'
import { Card, CardHeader, CardBody } from '../_design-system/card'
import { StatusDot, type StatusDotProps } from '../_design-system/status-dot'
import { Badge, type BadgeProps } from '../_design-system/badge'

const statusIntent: Record<Job['status'], NonNullable<StatusDotProps['intent']> & NonNullable<BadgeProps['intent']>> = {
  running:   'primary',
  completed: 'success',
  failed:    'danger',
  pending:   'warning',
  cancelled: 'neutral',
}

export function RecentActivityCard() {
  const { data: jobs, isLoading } = useJobs()
  const recent = (jobs ?? []).slice(0, 10)

  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Recent Activity"
        actions={isLoading ? <Loader2 size={14} className="animate-spin text-zinc-500" /> : undefined}
      />
      <CardBody className="flex-1 flex flex-col gap-3">
        {recent.length === 0 ? (
          <p className="text-xs text-zinc-500">No recent activity</p>
        ) : (
          <ul className="space-y-2.5">
            {recent.map(job => {
              const intent = statusIntent[job.status] ?? 'neutral'
              return (
                <li key={job.id} className="flex items-start gap-3">
                  <StatusDot intent={intent} className="mt-1.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        to={`/jobs/${job.id}`}
                        className="text-xs text-zinc-200 hover:text-white truncate"
                      >
                        {job.workspace}
                      </Link>
                      <span className="text-zinc-600 text-[10px] font-mono shrink-0">
                        {formatRelative(job.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1">
                      <Badge intent={intent}>{job.status}</Badge>
                      <span className="text-zinc-600 text-[10px] uppercase tracking-wider">{job.type}</span>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}

        <Link
          to="/jobs"
          className="mt-auto inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          Full job history <ArrowRight size={12} />
        </Link>
      </CardBody>
    </Card>
  )
}
