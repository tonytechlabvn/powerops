// VCS connection configuration panel — trigger patterns and connection status (Phase 4)
// Shows: repo info, trigger pattern editor (branch→action), auto-apply toggle, connection status

import { useState } from 'react'
import { GitBranch, GitPullRequest, CheckCircle2, AlertCircle, Save, RotateCcw } from 'lucide-react'
import { useVCSWorkflowConfig, useUpdateVCSWorkflowConfig } from '../../hooks/use-vcs-workflow'
import type { TriggerPattern } from '../../types/api-types'
import { cn } from '../../lib/utils'

interface VCSConnectionConfigPanelProps {
  workspaceId: string
}

const ACTION_LABELS: Record<string, { label: string; cls: string }> = {
  apply: { label: 'Auto-apply', cls: 'text-green-400 bg-green-900/30 border-green-800/50' },
  plan:  { label: 'Plan only',  cls: 'text-blue-400 bg-blue-900/30 border-blue-800/50'  },
}

function PatternRow({
  pattern,
  index,
  onChange,
  onRemove,
}: {
  pattern: TriggerPattern
  index: number
  onChange: (i: number, field: keyof TriggerPattern, value: string) => void
  onRemove: (i: number) => void
}) {
  const actionCfg = ACTION_LABELS[pattern.action] ?? ACTION_LABELS.plan
  return (
    <div className="flex items-center gap-2 group">
      <span className="text-xs text-zinc-600 w-4 shrink-0">{index + 1}.</span>
      <input
        value={pattern.branch}
        onChange={e => onChange(index, 'branch', e.target.value)}
        placeholder="main, feature/*, develop"
        className="flex-1 px-2.5 py-1.5 rounded-md bg-zinc-800 border border-zinc-700 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500 transition-colors"
      />
      <GitBranch size={12} className="text-zinc-600 shrink-0" />
      <select
        value={pattern.action}
        onChange={e => onChange(index, 'action', e.target.value)}
        className="px-2 py-1.5 rounded-md bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 transition-colors"
      >
        <option value="plan">plan</option>
        <option value="apply">apply</option>
      </select>
      <span className={cn('hidden group-hover:inline-flex items-center px-1.5 py-0.5 rounded text-xs border', actionCfg.cls)}>
        {actionCfg.label}
      </span>
      <button
        onClick={() => onRemove(index)}
        className="text-zinc-700 hover:text-red-400 transition-colors text-sm leading-none px-1"
        title="Remove pattern"
      >
        ×
      </button>
    </div>
  )
}

export function VCSConnectionConfigPanel({ workspaceId }: VCSConnectionConfigPanelProps) {
  const { data: config, isLoading, error } = useVCSWorkflowConfig(workspaceId)
  const updateConfig = useUpdateVCSWorkflowConfig(workspaceId)

  const [localPatterns, setLocalPatterns] = useState<TriggerPattern[] | null>(null)
  const [localAutoApply, setLocalAutoApply] = useState<boolean | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const patterns = localPatterns ?? config?.trigger_patterns ?? []
  const autoApply = localAutoApply ?? config?.auto_apply ?? false
  const isDirty = localPatterns !== null || localAutoApply !== null

  const handlePatternChange = (i: number, field: keyof TriggerPattern, value: string) => {
    const updated = patterns.map((p, idx) => idx === i ? { ...p, [field]: value } : p)
    setLocalPatterns(updated)
  }

  const handleRemovePattern = (i: number) => {
    setLocalPatterns(patterns.filter((_, idx) => idx !== i))
  }

  const handleAddPattern = () => {
    setLocalPatterns([...patterns, { branch: '', action: 'plan' }])
  }

  const handleReset = () => {
    setLocalPatterns(null)
    setLocalAutoApply(null)
    setSaveSuccess(false)
  }

  const handleSave = async () => {
    const valid = patterns.filter(p => (p.branch || '').trim())
    await updateConfig.mutateAsync({ trigger_patterns: valid, auto_apply: autoApply })
    setLocalPatterns(null)
    setLocalAutoApply(null)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  if (isLoading) {
    return <div className="p-5 text-sm text-zinc-500">Loading VCS connection...</div>
  }

  if (error || !config) {
    return (
      <div className="p-5 flex items-center gap-2 text-sm text-zinc-500">
        <AlertCircle size={14} className="text-amber-400" />
        No VCS connection configured for this workspace.
      </div>
    )
  }

  return (
    <div className="p-5 space-y-5">
      {/* Connection status bar */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-950 border border-zinc-800">
        <div className="flex items-center gap-3">
          <CheckCircle2 size={14} className="text-green-400 shrink-0" />
          <div>
            <p className="text-sm font-medium text-zinc-200 font-mono">{config.repo_full_name}</p>
            <p className="text-xs text-zinc-500 mt-0.5 flex items-center gap-1">
              <GitBranch size={10} />
              tracking <span className="font-mono">{config.branch}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <GitPullRequest size={12} className="text-zinc-500" />
          <span className="text-xs text-zinc-500">GitHub App connected</span>
        </div>
      </div>

      {/* Auto-apply toggle */}
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          id="auto-apply-toggle"
          checked={autoApply}
          onChange={e => setLocalAutoApply(e.target.checked)}
          className="mt-0.5 accent-blue-500"
        />
        <label htmlFor="auto-apply-toggle" className="cursor-pointer select-none">
          <p className="text-sm font-medium text-zinc-200">Auto-apply on merge</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            Automatically run terraform apply when a PR merges to a branch with action=apply
          </p>
        </label>
      </div>

      {/* Trigger patterns */}
      <div className="space-y-3">
        <div>
          <p className="text-sm font-semibold text-zinc-200">Trigger Patterns</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            Evaluated in order — first matching branch pattern wins. Supports glob: <code className="font-mono bg-zinc-800 px-1 rounded">feature/*</code>
          </p>
        </div>
        <div className="space-y-2">
          {patterns.map((p, i) => (
            <PatternRow
              key={i}
              pattern={p}
              index={i}
              onChange={handlePatternChange}
              onRemove={handleRemovePattern}
            />
          ))}
        </div>
        <button
          onClick={handleAddPattern}
          className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          + Add pattern
        </button>
      </div>

      {/* Action bar */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleSave}
          disabled={!isDirty || updateConfig.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40 transition-colors"
        >
          <Save size={13} />
          {updateConfig.isPending ? 'Saving...' : 'Save'}
        </button>
        {isDirty && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          >
            <RotateCcw size={13} />
            Reset
          </button>
        )}
        {saveSuccess && (
          <span className="flex items-center gap-1 text-xs text-green-400">
            <CheckCircle2 size={12} />
            Saved
          </span>
        )}
      </div>
    </div>
  )
}
