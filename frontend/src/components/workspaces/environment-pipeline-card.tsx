// Visual card for a single environment in the pipeline view (Phase 2)
// Shows: name, workspace count, last deploy status, auto-apply/require-approval badges
// Arrow connector indicates promotion flow to next environment

import { ChevronRight, Zap, Shield, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { Environment } from '../../types/api-types'

interface EnvironmentPipelineCardProps {
  environment: Environment
  isLast: boolean
  isSelected: boolean
  onSelect: () => void
}

function StatusIcon({ status }: { status: string | undefined }) {
  if (status === 'applied') return <CheckCircle2 size={14} className="text-green-400" />
  if (status === 'failed')  return <XCircle size={14} className="text-red-400" />
  return <Clock size={14} className="text-zinc-500" />
}

function StatusLabel({ status }: { status: string | undefined }) {
  if (status === 'applied') return <span className="text-green-400">Applied</span>
  if (status === 'failed')  return <span className="text-red-400">Failed</span>
  return <span className="text-zinc-500">No runs yet</span>
}

export function EnvironmentPipelineCard({
  environment,
  isLast,
  isSelected,
  onSelect,
}: EnvironmentPipelineCardProps) {
  const lastStatus = undefined // would come from last run in real data

  return (
    <div className="flex items-center gap-0">
      {/* Card */}
      <button
        onClick={onSelect}
        className={cn(
          'flex flex-col gap-3 p-4 rounded-lg border w-52 text-left transition-all',
          isSelected
            ? 'border-blue-500 bg-blue-600/10 shadow-md shadow-blue-900/20'
            : 'border-zinc-800 bg-zinc-900 hover:border-zinc-700 hover:bg-zinc-800/60',
        )}
      >
        {/* Color dot + name */}
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: environment.color }}
          />
          <span className="text-sm font-semibold text-zinc-100 truncate">{environment.name}</span>
        </div>

        {/* Description */}
        {environment.description && (
          <p className="text-xs text-zinc-500 leading-relaxed line-clamp-2">
            {environment.description}
          </p>
        )}

        {/* Stats row */}
        <div className="flex items-center justify-between text-xs text-zinc-400">
          <span>{environment.workspace_count} workspace{environment.workspace_count !== 1 ? 's' : ''}</span>
          <span>{environment.variable_count} vars</span>
        </div>

        {/* Last deploy status */}
        <div className="flex items-center gap-1.5 text-xs">
          <StatusIcon status={lastStatus} />
          <StatusLabel status={lastStatus} />
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5">
          {environment.auto_apply && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-green-900/40 text-green-400 border border-green-800/50">
              <Zap size={10} />
              Auto-apply
            </span>
          )}
          {environment.is_protected && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-amber-900/40 text-amber-400 border border-amber-800/50">
              <Shield size={10} />
              Protected
            </span>
          )}
        </div>
      </button>

      {/* Arrow connector to next env */}
      {!isLast && (
        <div className="flex items-center px-1 text-zinc-600">
          <ChevronRight size={20} />
        </div>
      )}
    </div>
  )
}
