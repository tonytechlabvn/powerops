// Stack Template list panel — browse saved stack templates and instantiate them

import { useState } from 'react'
import { Layers, Play, Trash2, ChevronRight, Tag } from 'lucide-react'
import { useStackTemplates, useDeleteStackTemplate, useCreateProjectFromTemplate } from '../../hooks/use-stacks'
import type { StackTemplate } from '../../types/api-types'

interface Props {
  /** Called after a project is created from a template */
  onProjectCreated?: (projectId: string) => void
}

export function StackTemplateListPanel({ onProjectCreated }: Props) {
  const { data: templates = [], isLoading } = useStackTemplates()
  const deleteTemplate = useDeleteStackTemplate()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [deployingId, setDeployingId] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')
  const [error, setError] = useState('')

  const createProject = useCreateProjectFromTemplate(deployingId ?? '')

  function toggleExpand(id: string) {
    setExpandedId(prev => prev === id ? null : id)
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this stack template?')) return
    try {
      await deleteTemplate.mutateAsync(id)
    } catch {
      setError('Failed to delete template')
    }
  }

  function startDeploy(id: string) {
    setDeployingId(id)
    setProjectName('')
    setError('')
  }

  async function handleCreate() {
    if (!projectName.trim()) { setError('Project name is required'); return }
    if (!deployingId) return
    setError('')
    try {
      const result = await createProject.mutateAsync({ project_name: projectName.trim() })
      setDeployingId(null)
      onProjectCreated?.(result.project_id ?? '')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create project')
    }
  }

  if (isLoading) {
    return <div className="text-sm text-zinc-400 p-4">Loading templates...</div>
  }

  if (templates.length === 0) {
    return (
      <div className="text-center py-10 text-zinc-500">
        <Layers size={32} className="mx-auto mb-2 opacity-30" />
        <p className="text-sm">No stack templates saved yet.</p>
        <p className="text-xs mt-1 text-zinc-600">Use the Stack Composer to build and save one.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {templates.map(tpl => (
        <TemplateCard
          key={tpl.id}
          template={tpl}
          expanded={expandedId === tpl.id}
          onToggle={() => toggleExpand(tpl.id)}
          onDelete={() => handleDelete(tpl.id)}
          onDeploy={() => startDeploy(tpl.id)}
        />
      ))}

      {/* Deploy modal */}
      {deployingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-80 bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-100">Create Project from Template</h3>
            <div className="space-y-1">
              <label className="text-xs text-zinc-400">Project name</label>
              <input
                value={projectName}
                onChange={e => setProjectName(e.target.value)}
                placeholder="my-project"
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
                autoFocus
              />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeployingId(null)}
                className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createProject.isPending}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded disabled:opacity-50"
              >
                {createProject.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Template card
// ---------------------------------------------------------------------------

function TemplateCard({
  template,
  expanded,
  onToggle,
  onDelete,
  onDeploy,
}: {
  template: StackTemplate
  expanded: boolean
  onToggle: () => void
  onDelete: () => void
  onDeploy: () => void
}) {
  const definition = (() => {
    try { return JSON.parse(template.definition_json || '{}') } catch { return {} }
  })()
  const modules: Array<{ name: string; source: string; version: string }> =
    definition.modules ?? []

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-zinc-800/40 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Layers size={15} className="text-blue-400 shrink-0" />
          <span className="text-sm font-medium text-zinc-100 truncate">{template.name}</span>
          <span className="text-xs text-zinc-500 shrink-0">{template.module_count ?? modules.length} modules</span>
        </div>
        <ChevronRight
          size={14}
          className={`text-zinc-600 shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-zinc-800">
          {template.description && (
            <p className="text-xs text-zinc-400 mt-3">{template.description}</p>
          )}

          {/* Module list */}
          <div className="space-y-1">
            {modules.map(m => (
              <div
                key={m.name}
                className="flex items-center justify-between text-xs px-2 py-1.5 bg-zinc-950 rounded"
              >
                <span className="text-zinc-300 font-mono">{m.name}</span>
                <span className="text-zinc-500">{m.source} @ v{m.version}</span>
              </div>
            ))}
          </div>

          {/* Tags */}
          {(template.tags ?? []).length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {(template.tags ?? []).map(tag => (
                <span key={tag} className="flex items-center gap-0.5 px-2 py-0.5 bg-zinc-800 text-zinc-500 text-xs rounded-full">
                  <Tag size={9} />{tag}
                </span>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={onDeploy}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded transition-colors"
            >
              <Play size={12} /> Use Template
            </button>
            <button
              onClick={onDelete}
              className="flex items-center gap-1.5 px-2 py-1.5 text-zinc-500 hover:text-red-400 text-xs rounded transition-colors"
            >
              <Trash2 size={12} /> Delete
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
