// Colored display of Terraform plan resource changes (add/change/destroy)

import type { PlanSummary, ResourceChange } from '../../types/api-types'
import { actionColor, actionSymbol } from '../../lib/utils'

interface PlanDiffDisplayProps {
  planSummary: PlanSummary
}

function ResourceRow({ resource }: { resource: ResourceChange }) {
  return (
    <div className="font-mono text-xs py-1 border-b border-zinc-800 last:border-0">
      <span className={`font-bold mr-2 ${actionColor(resource.action)}`}>
        {actionSymbol(resource.action)}
      </span>
      <span className={actionColor(resource.action)}>
        {resource.type}.{resource.name}
      </span>
      <span className="text-zinc-500 ml-2">({resource.address})</span>
    </div>
  )
}

function SummaryBadge({ label, count, color }: { label: string; count: number; color: string }) {
  if (count === 0) return null
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${color}`}>
      <span className="font-bold">{count}</span> {label}
    </span>
  )
}

export function PlanDiffDisplay({ planSummary }: PlanDiffDisplayProps) {
  const { adds, changes, destroys, resources, cost_estimate } = planSummary

  return (
    <div className="space-y-4">
      {/* Summary counts */}
      <div className="flex flex-wrap gap-2">
        <SummaryBadge
          label="to add"
          count={adds}
          color="bg-green-500/20 text-green-400 border-green-500/30"
        />
        <SummaryBadge
          label="to change"
          count={changes}
          color="bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
        />
        <SummaryBadge
          label="to destroy"
          count={destroys}
          color="bg-red-500/20 text-red-400 border-red-500/30"
        />
        {adds === 0 && changes === 0 && destroys === 0 && (
          <span className="text-xs text-zinc-500">No changes. Infrastructure is up-to-date.</span>
        )}
      </div>

      {/* Cost estimate */}
      {cost_estimate && (
        <div className="text-sm text-zinc-400">
          Estimated cost: <span className="text-zinc-200 font-medium">{cost_estimate}</span>
        </div>
      )}

      {/* Resource list */}
      {resources.length > 0 && (
        <div className="rounded border border-zinc-800 bg-zinc-950 p-4 overflow-x-auto">
          <p className="text-xs text-zinc-500 mb-3 uppercase tracking-wider">Resource Changes</p>
          {resources.map((r, i) => (
            <ResourceRow key={`${r.address}-${i}`} resource={r} />
          ))}
        </div>
      )}
    </div>
  )
}
