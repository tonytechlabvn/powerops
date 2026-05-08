// Environments pipeline page — shows dev/staging/prod as a visual flow (Phase 2)
// Allows creating environments, linking workspaces, and viewing per-env workspace list

import { useState } from 'react'
import { Plus, RefreshCw, Link2 } from 'lucide-react'
import { useEnvironments, useCreateEnvironment } from '../../hooks/use-environments'
import { EnvironmentPipelineCard } from './environment-pipeline-card'
import type { Environment } from '../../types/api-types'
import { Button } from '../_design-system/button'
import { Card, CardHeader, CardBody } from '../_design-system/card'
import { Input } from '../_design-system/input'
import { EmptyState } from '../_design-system/empty-state'

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <Card className="w-full max-w-md shadow-2xl">
        <CardHeader title="Create Environment" />
        <CardBody>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">Name</label>
              <Input value={name} onChange={e => setName(e.target.value)} required placeholder="dev / staging / prod" />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">Description</label>
              <Input value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" />
            </div>
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Color</label>
                <input type="color" value={color} onChange={e => setColor(e.target.value)}
                  className="h-9 w-full rounded-md border border-zinc-800 bg-zinc-900 cursor-pointer"
                />
              </div>
              <div className="flex items-end gap-4 pb-0.5">
                <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                  <input type="checkbox" checked={autoApply} onChange={e => setAutoApply(e.target.checked)} className="accent-blue-500" />
                  Auto-apply
                </label>
                <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                  <input type="checkbox" checked={isProtected} onChange={e => setIsProtected(e.target.checked)} className="accent-amber-500" />
                  Protected
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button intent="ghost" type="button" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={create.isPending || !name.trim()}>
                {create.isPending ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Environments</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Organize workspaces into promotion pipelines (dev → staging → prod)
          </p>
        </div>
        <div className="flex gap-2">
          <Button intent="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw size={14} /> Refresh
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus size={14} /> New Environment
          </Button>
        </div>
      </div>

      {/* Pipeline visual */}
      {environments.length === 0 ? (
        <EmptyState
          title="No environments yet"
          description="Create your first environment to start organizing promotion pipelines."
          action={<Button onClick={() => setShowCreate(true)}><Plus size={16} />New Environment</Button>}
        />
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
        <Card>
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: selectedEnv.color }} />
                {selectedEnv.name} <span className="text-zinc-500 font-normal">— Workspaces</span>
              </span>
            }
          />
          <CardBody>
            <EnvironmentWorkspaceList environment={selectedEnv} />
          </CardBody>
        </Card>
      )}

      {showCreate && (
        <CreateEnvironmentDialog orgId={ORG_ID} onClose={() => setShowCreate(false)} />
      )}
    </div>
  )
}
