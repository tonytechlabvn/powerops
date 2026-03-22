// Environments pipeline page — shows dev/staging/prod as a visual flow (Phase 2)
// Allows creating environments, linking workspaces, and viewing per-env workspace list

import { useState } from 'react'
import { Plus, RefreshCw, Link2 } from 'lucide-react'
import { useEnvironments, useCreateEnvironment } from '../../hooks/use-environments'
import { EnvironmentPipelineCard } from './environment-pipeline-card'
import type { Environment } from '../../types/api-types'

// Hardcoded org_id — in production this comes from auth context / org switcher
const ORG_ID = 'default-org'

interface CreateDialogProps {
  orgId: string
  onClose: () => void
}

function CreateEnvironmentDialog({ orgId, onClose }: CreateDialogProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState('#6366f1')
  const [autoApply, setAutoApply] = useState(false)
  const [isProtected, setIsProtected] = useState(false)
  const create = useCreateEnvironment()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await create.mutateAsync({ name, description, color, auto_apply: autoApply, is_protected: isProtected, org_id: orgId })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-zinc-100 mb-4">Create Environment</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Name</label>
            <input
              value={name} onChange={e => setName(e.target.value)} required
              placeholder="dev / staging / prod"
              className="w-full px-3 py-2 rounded-md bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Description</label>
            <input
              value={description} onChange={e => setDescription(e.target.value)}
              placeholder="Optional description"
              className="w-full px-3 py-2 rounded-md bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-xs text-zinc-400 mb-1">Color</label>
              <input type="color" value={color} onChange={e => setColor(e.target.value)}
                className="h-9 w-full rounded-md bg-zinc-800 border border-zinc-700 cursor-pointer"
              />
            </div>
            <div className="flex items-end gap-4 pb-0.5">
              <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                <input type="checkbox" checked={autoApply} onChange={e => setAutoApply(e.target.checked)}
                  className="accent-blue-500"
                />
                Auto-apply
              </label>
              <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                <input type="checkbox" checked={isProtected} onChange={e => setIsProtected(e.target.checked)}
                  className="accent-amber-500"
                />
                Protected
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm rounded-md text-zinc-400 hover:text-zinc-100 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={create.isPending || !name.trim()}
              className="px-4 py-2 text-sm rounded-md bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-50 transition-colors">
              {create.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EnvironmentWorkspaceList({ environment }: { environment: Environment }) {
  if (environment.workspace_count === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-zinc-600">
        <Link2 size={24} className="mb-2" />
        <p className="text-sm">No workspaces linked</p>
        <p className="text-xs mt-1">Link a workspace via the workspace settings</p>
      </div>
    )
  }
  return (
    <p className="text-sm text-zinc-400 py-4">
      {environment.workspace_count} workspace{environment.workspace_count !== 1 ? 's' : ''} linked.
      Select from Workspace settings to manage.
    </p>
  )
}

export function WorkspaceEnvironmentPage() {
  const { data: environments = [], isLoading, refetch } = useEnvironments(ORG_ID)
  const [showCreate, setShowCreate] = useState(false)
  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-500 text-sm">
        Loading environments...
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Environments</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Organize workspaces into promotion pipelines (dev → staging → prod)
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => refetch()}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors">
            <RefreshCw size={14} />
            Refresh
          </button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors">
            <Plus size={14} />
            New Environment
          </button>
        </div>
      </div>

      {/* Pipeline visual */}
      {environments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-600">
          <p className="text-sm mb-2">No environments yet</p>
          <button onClick={() => setShowCreate(true)}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
            Create your first environment
          </button>
        </div>
      ) : (
        <div className="flex items-start gap-0 overflow-x-auto pb-2">
          {environments.map((env, idx) => (
            <EnvironmentPipelineCard
              key={env.id}
              environment={env}
              isLast={idx === environments.length - 1}
              isSelected={selectedEnv?.id === env.id}
              onSelect={() => setSelectedEnv(env.id === selectedEnv?.id ? null : env)}
            />
          ))}
        </div>
      )}

      {/* Detail panel for selected environment */}
      {selectedEnv && (
        <div className="border border-zinc-800 rounded-lg bg-zinc-900 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: selectedEnv.color }} />
              {selectedEnv.name} — Workspaces
            </h2>
          </div>
          <EnvironmentWorkspaceList environment={selectedEnv} />
        </div>
      )}

      {showCreate && (
        <CreateEnvironmentDialog orgId={ORG_ID} onClose={() => setShowCreate(false)} />
      )}
    </div>
  )
}
