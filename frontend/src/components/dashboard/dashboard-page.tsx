// Dashboard: KPI strip + 3-card overview grid.

import { useMemo } from 'react'
import { Briefcase, ShieldCheck, Layers, TrendingUp } from 'lucide-react'
import { useJobs, useApprovals } from '../../hooks/use-api'
import { Card, CardBody } from '../_design-system/card'
import { ActiveJobsCard } from './active-jobs-card'
import { PendingApprovalsCard } from './pending-approvals-card'
import { RecentActivityCard } from './recent-activity-card'
import type { LucideIcon } from 'lucide-react'

interface KpiProps {
  label: string
  value: string | number
  icon: LucideIcon
  hint?: string
  intent?: 'neutral' | 'success' | 'warning' | 'primary'
}

function Kpi({ label, value, icon: Icon, hint, intent = 'neutral' }: KpiProps) {
  const valueClass =
    intent === 'success' ? 'text-emerald-400'
    : intent === 'warning' ? 'text-amber-400'
    : intent === 'primary' ? 'text-blue-400'
    : 'text-zinc-100'

  return (
    <Card>
      <CardBody className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider font-medium text-zinc-500">{label}</div>
          <div className={`mt-2 text-2xl font-semibold ${valueClass}`}>{value}</div>
          {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
        </div>
        <div className="h-9 w-9 rounded-md bg-zinc-800/60 text-zinc-400 flex items-center justify-center shrink-0">
          <Icon size={16} />
        </div>
      </CardBody>
    </Card>
  )
}

export function DashboardPage() {
  const { data: jobs } = useJobs()
  const { data: approvals } = useApprovals()

  const stats = useMemo(() => {
    const allJobs = jobs ?? []
    const running = allJobs.filter(j => j.status === 'running').length
    const completed = allJobs.filter(j => j.status === 'completed').length
    const failed = allJobs.filter(j => j.status === 'failed').length
    const total = completed + failed
    const successRate = total > 0 ? Math.round((completed / total) * 100) : null
    const workspaces = new Set(allJobs.map(j => j.workspace).filter(Boolean)).size
    const pendingApprovals = (approvals ?? []).filter(a => a.status === 'pending').length

    return { running, pendingApprovals, workspaces, successRate }
  }, [jobs, approvals])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Dashboard</h1>
        <p className="text-sm text-zinc-400 mt-1">Overview of your Terraform infrastructure</p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Active Jobs"        value={stats.running}              icon={Briefcase}    intent="primary" />
        <Kpi label="Pending Approvals"  value={stats.pendingApprovals}     icon={ShieldCheck}  intent={stats.pendingApprovals > 0 ? 'warning' : 'neutral'} />
        <Kpi label="Workspaces"         value={stats.workspaces}           icon={Layers} />
        <Kpi label="Apply Success Rate" value={stats.successRate !== null ? `${stats.successRate}%` : '—'} icon={TrendingUp} intent="success" hint="completed vs failed" />
      </div>

      {/* 3-card grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActiveJobsCard />
        <PendingApprovalsCard />
        <RecentActivityCard />
      </div>
    </div>
  )
}
