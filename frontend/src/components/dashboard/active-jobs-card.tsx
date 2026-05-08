// Dashboard card showing active jobs as a DataTable inline (Stitch-inspired layout).

import { Link, useNavigate } from 'react-router-dom'
import { Loader2, ArrowRight } from 'lucide-react'
import { useJobs } from '../../hooks/use-api'
import { formatRelative } from '../../lib/utils'
import type { Job } from '../../types/api-types'
import { Card, CardHeader, CardBody } from '../_design-system/card'
import { Badge, type BadgeProps } from '../_design-system/badge'
import { DataTable, type Column } from '../_design-system/data-table'
import { EmptyState } from '../_design-system/empty-state'

const intentByStatus: Record<Job['status'], NonNullable<BadgeProps['intent']>> = {
  running: 'primary',
  completed: 'success',
  failed: 'danger',
  pending: 'warning',
  cancelled: 'neutral',
}

export function ActiveJobsCard() {
  const navigate = useNavigate()
  const { data: jobs, isLoading } = useJobs()
  const activeOrRecent = (jobs ?? []).slice(0, 6)

  const columns: Column<Job>[] = [
    {
      key: 'status',
      header: 'Status',
      className: 'w-24',
      render: (j) => <Badge intent={intentByStatus[j.status] ?? 'neutral'}>{j.status}</Badge>,
    },
    {
      key: 'workspace',
      header: 'Workspace',
      render: (j) => (
        <span className="font-mono text-xs text-zinc-200 truncate block max-w-[180px]">{j.workspace}</span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      className: 'w-20',
      render: (j) => <span className="text-xs uppercase tracking-wider text-zinc-500">{j.type}</span>,
    },
    {
      key: 'created_at',
      header: 'Started',
      className: 'w-24 text-right',
      align: 'right',
      render: (j) => <span className="font-mono text-xs text-zinc-500">{formatRelative(j.created_at)}</span>,
    },
  ]

  return (
    <Card className="flex flex-col h-full">
      <CardHeader
        title="Active Jobs"
        subtitle={`${activeOrRecent.length} most recent`}
        actions={
          <Link
            to="/jobs"
            className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            View all <ArrowRight size={12} />
          </Link>
        }
      />
      <CardBody className="p-0 flex-1">
        {isLoading ? (
          <div className="flex items-center gap-2 px-6 py-8 text-sm text-zinc-500">
            <Loader2 size={14} className="animate-spin" /> Loading…
          </div>
        ) : activeOrRecent.length === 0 ? (
          <div className="px-6 py-6">
            <EmptyState title="No jobs yet" description="Trigger a Terraform plan or apply to see jobs here." />
          </div>
        ) : (
          <DataTable
            className="border-0 rounded-none"
            columns={columns}
            rows={activeOrRecent}
            getRowKey={(r) => r.id}
            onRowClick={(r) => navigate(`/jobs/${r.id}`)}
          />
        )}
      </CardBody>
    </Card>
  )
}
