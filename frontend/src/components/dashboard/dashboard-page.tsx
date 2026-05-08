// Dashboard: KPI strip with trends + 2-col main + pending approvals section.

import { useMemo } from 'react'
import { Briefcase, ShieldCheck, Layers, TrendingUp, AlertCircle, ArrowUpRight, CheckCircle2 } from 'lucide-react'
import { useJobs, useApprovals } from '../../hooks/use-api'
import { Card, CardBody } from '../_design-system/card'
import { ActiveJobsCard } from './active-jobs-card'
import { RecentActivityCard } from './recent-activity-card'
import { DashboardPendingApprovalsSection } from './dashboard-pending-approvals-section'
import type { LucideIcon } from 'lucide-react'

interface KpiTrend {
  label: string
  intent: 'success' | 'warning' | 'danger' | 'neutral'
  icon?: LucideIcon
}

interface KpiProps {
  label: string
  value: string | number
  icon: LucideIcon
  hint: string
  trend?: KpiTrend
}

function Kpi({ label, value, icon: Icon, hint, trend }: KpiProps) {
  const trendCls = trend
    ? trend.intent === 'success' ? 'text-emerald-400 bg-emerald-500/10 ring-emerald-500/20'
    : trend.intent === 'warning' ? 'text-amber-400 bg-amber-500/10 ring-amber-500/20'
    : trend.intent === 'danger'  ? 'text-red-400 bg-red-500/10 ring-red-500/20'
    : 'text-zinc-300 bg-zinc-800/60 ring-zinc-700/40'
    : ''

  return (
    <Card className="group hover:border-zinc-700 transition-colors duration-150">
      <CardBody className="flex flex-col gap-1.5">
        <div className="flex items-start justify-between gap-2">
          <span className="text-sm font-medium text-zinc-400">{label}</span>
          {trend ? (
            <span className={`inline-flex items-center gap-0.5 text-[11px] font-mono font-medium px-1.5 py-0.5 rounded ring-1 ring-inset ${trendCls}`}>
              {trend.icon && <trend.icon size={11} />}
              {trend.label}
            </span>
          ) : (
            <Icon size={16} className="text-zinc-500 shrink-0 mt-0.5" />
          )}
        </div>
        <div className="text-3xl font-semibold text-zinc-100 leading-tight">{value}</div>
        <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">{hint}</div>
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
    const pending = (approvals ?? []).filter(a => a.status === 'pending')

    return {
      running,
      pendingCount: pending.length,
      criticalApprovals: pending.filter(a => (a.plan_summary?.destroys ?? 0) > 0).length,
      workspaces,
      successRate,
      successOptimal: successRate !== null && successRate >= 95,
    }
  }, [jobs, approvals])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Dashboard</h1>
        <p className="text-sm text-zinc-400 mt-1">Overview of your Terraform infrastructure</p>
      </div>

      {/* KPI strip with trend indicators */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi
          label="Active Jobs"
          value={stats.running}
          icon={Briefcase}
          hint="Currently Running"
          trend={stats.running > 0 ? { label: 'Live', intent: 'success', icon: ArrowUpRight } : undefined}
        />
        <Kpi
          label="Pending Approvals"
          value={stats.pendingCount}
          icon={ShieldCheck}
          hint={stats.pendingCount > 0 ? 'Requires Intervention' : 'All clear'}
          trend={
            stats.criticalApprovals > 0
              ? { label: `${stats.criticalApprovals} Critical`, intent: 'danger', icon: AlertCircle }
              : stats.pendingCount > 0
                ? { label: 'Review', intent: 'warning' }
                : undefined
          }
        />
        <Kpi
          label="Workspaces"
          value={stats.workspaces}
          icon={Layers}
          hint={stats.workspaces > 0 ? `Across deployments` : 'No workspaces yet'}
        />
        <Kpi
          label="Apply Success Rate"
          value={stats.successRate !== null ? `${stats.successRate}%` : '—'}
          icon={TrendingUp}
          hint="Completed vs Failed"
          trend={
            stats.successOptimal
              ? { label: 'Optimal', intent: 'success', icon: CheckCircle2 }
              : stats.successRate !== null && stats.successRate < 80
                ? { label: 'Degraded', intent: 'warning' }
                : undefined
          }
        />
      </div>

      {/* 2-col main: Active Jobs (2/3) + Recent Activity (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ActiveJobsCard />
        </div>
        <RecentActivityCard />
      </div>

      {/* Pending Approvals section with inline diff + Approve/Reject */}
      <DashboardPendingApprovalsSection />
    </div>
  )
}
