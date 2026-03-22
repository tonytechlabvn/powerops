// VCS workflow configuration panel for a workspace (Phase 4)
// Shows: trigger patterns config, auto-plan/apply toggles, VCS run history, manual replan

import { useState } from 'react'
import { GitBranch, Play, RefreshCw, Settings, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import { useVCSWorkflowConfig, useUpdateVCSWorkflowConfig, useVCSPRPlans, useManualReplan } from '../../hooks/use-vcs-workflow'
import type { VCSPlanRun, TriggerPattern } from '../../types/api-types'
import { cn } from '../../lib/utils'

interface VCSWorkflowPanelProps {
  workspaceId: string
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; icon: React.ReactNode; cls: string }> = {
    completed: { label: 'Passed',    icon: <CheckCircle2 size={12} />, cls: 'text-green-400 bg-green-900/30 border-green-800/50' },
    failed:    { label: 'Failed',    icon: <XCircle size={12} />,      cls: 'text-red-400 bg-red-900/30 border-red-800/50' },
    running:   { label: 'Running',   icon: <Loader2 size={12} className="animate-spin" />, cls: 'text-blue-400 bg-blue-900/30 border-blue-800/50' },
    cancelled: { label: 'Cancelled', icon: <XCircle size={12} />,      cls: 'text-zinc-500 bg-zinc-800 border-zinc-700' },
    pending:   { label: 'Pending',   icon: <Clock size={12} />,        cls: 'text-amber-400 bg-amber-900/30 border-amber-800/50' },
  }
  const { label, icon, cls } = map[status] ?? map.pending
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border', cls)}>
      {icon}{label}
    </span>
  )
}

function PlanRunRow({ run, workspaceId }: { run: VCSPlanRun; workspaceId: string }) {
  const replan = useManualReplan(workspaceId)
  const [expanded, setExpanded] = useState(false)

  let summary = { adds: 0, changes: 0, destroys: 0 }
  try { summary = JSON.parse(run.plan_summary_json || '{}') } catch { /* ignore */ }

  return (
    <div className="border border-zinc-800 rounded-lg bg-zinc-950 overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <StatusBadge status={run.status} />
        <span className="text-xs text-zinc-400 font-mono">#{run.pr_number}</span>
        <span className="text-xs font-mono text-zinc-500">{run.commit_sha.slice(0, 8)}</span>
        <span className="text-xs text-zinc-500 flex-1 truncate">{run.branch}</span>
        <span className="text-xs text-zinc-600">
          +{summary.adds} ~{summary.changes} -{summary.destroys}
        </span>
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors px-2"
        >
          {expanded ? 'Hide' : 'Output'}
        </button>
        <button
          onClick={() => run.pr_number && replan.mutate({ prNumber: run.pr_number })}
          disabled={replan.isPending}
          className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50 transition-colors"
        >
          <Play size={11} />
          Re-plan
        </button>
      </div>
      {expanded && run.plan_output && (
        <pre className="px-4 pb-4 text-xs text-zinc-400 font-mono whitespace-pre-wrap max-h-64 overflow-y-auto border-t border-zinc-800 pt-3">
          {run.plan_output.slice(0, 4000)}
          {run.plan_output.length > 4000 && '\n...(truncated)'}
        </pre>
      )}
    </div>
  )
}

function TriggerPatternEditor({
  patterns, onChange,
}: { patterns: TriggerPattern[]; onChange: (p: TriggerPattern[]) => void }) {
  const addPattern = () => onChange([...patterns, { branch: '', action: 'plan' }])
  const removePattern = (i: number) => onChange(patterns.filter((_, idx) => idx !== i))
  const updatePattern = (i: number, field: keyof TriggerPattern, value: string) => {
    onChange(patterns.map((p, idx) => idx === i ? { ...p, [field]: value } : p))
  }

  return (
    <div className="space-y-2">
      {patterns.map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            value={p.branch} onChange={e => updatePattern(i, 'branch', e.target.value)}
            placeholder="main, feature/*, *"
            className="flex-1 px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 font-mono focus:outline-none focus:border-blue-500"
          />
          <span className="text-zinc-600 text-xs">→</span>
          <select
            value={p.action} onChange={e => updatePattern(i, 'action', e.target.value)}
            className="px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
          >
            <option value="plan">plan</option>
            <option value="apply">apply</option>
          </select>
          <button onClick={() => removePattern(i)} className="text-zinc-600 hover:text-red-400 text-xs transition-colors px-1">
            ×
          </button>
        </div>
      ))}
      <button onClick={addPattern} className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
        + Add pattern
      </button>
    </div>
  )
}

export function VCSWorkflowPanel({ workspaceId }: VCSWorkflowPanelProps) {
  const { data: config, isLoading: configLoading } = useVCSWorkflowConfig(workspaceId)
  const { data: runs = [], isLoading: runsLoading, refetch } = useVCSPRPlans(workspaceId)
  const updateConfig = useUpdateVCSWorkflowConfig(workspaceId)
  const [editingPatterns, setEditingPatterns] = useState<TriggerPattern[] | null>(null)
  const [autoApply, setAutoApply] = useState<boolean | null>(null)

  const patterns = editingPatterns ?? config?.trigger_patterns ?? []
  const effectiveAutoApply = autoApply ?? config?.auto_apply ?? false

  const handleSaveConfig = async () => {
    await updateConfig.mutateAsync({ trigger_patterns: patterns, auto_apply: effectiveAutoApply })
    setEditingPatterns(null)
    setAutoApply(null)
  }

  if (configLoading) {
    return <div className="p-6 text-sm text-zinc-500">Loading VCS workflow config...</div>
  }

  if (!config) {
    return (
      <div className="p-6 text-sm text-zinc-500 flex items-center gap-2">
        <GitBranch size={16} />
        No VCS connection. Connect a repository first.
      </div>
    )
  }

  const isDirty = editingPatterns !== null || autoApply !== null

  return (
    <div className="p-5 space-y-6">
      {/* Config section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <Settings size={14} />
            Workflow Configuration
          </h3>
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <GitBranch size={12} />
            <span className="font-mono">{config.repo_full_name}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 mb-2">
          <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={effectiveAutoApply}
              onChange={e => setAutoApply(e.target.checked)}
              className="accent-blue-500"
            />
            Auto-apply on merge
          </label>
        </div>
        <TriggerPatternEditor
          patterns={patterns}
          onChange={p => setEditingPatterns(p)}
        />
        {isDirty && (
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleSaveConfig}
              disabled={updateConfig.isPending}
              className="px-3 py-1.5 text-xs rounded-md bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-50 transition-colors"
            >
              {updateConfig.isPending ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={() => { setEditingPatterns(null); setAutoApply(null) }}
              className="px-3 py-1.5 text-xs rounded-md text-zinc-400 hover:text-zinc-100 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Run history */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-200">VCS Plan History</h3>
          <button onClick={() => refetch()} className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors">
            <RefreshCw size={12} />
            Refresh
          </button>
        </div>
        {runsLoading ? (
          <p className="text-sm text-zinc-500">Loading run history...</p>
        ) : runs.length === 0 ? (
          <p className="text-sm text-zinc-600">No VCS-triggered plans yet.</p>
        ) : (
          <div className="space-y-2">
            {runs.slice(0, 20).map(run => (
              <PlanRunRow key={run.id} run={run} workspaceId={workspaceId} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
