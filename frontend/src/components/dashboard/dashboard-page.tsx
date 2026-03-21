// Main dashboard page with 3-card grid overview

import { ActiveJobsCard } from './active-jobs-card'
import { PendingApprovalsCard } from './pending-approvals-card'
import { RecentActivityCard } from './recent-activity-card'

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">Overview of your Terraform infrastructure</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActiveJobsCard />
        <PendingApprovalsCard />
        <RecentActivityCard />
      </div>
    </div>
  )
}
