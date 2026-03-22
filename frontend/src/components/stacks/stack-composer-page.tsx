// Stack Composer — visually assemble registry modules into a deployable stack

import { useState } from 'react'
import { Plus, Trash2, Eye, Save, Layers } from 'lucide-react'
import { useRegistryModules } from '../../hooks/use-module-registry'
import { useComposeProject, useCreateStackTemplate } from '../../hooks/use-stacks'
import type { StackModuleEntry, StackDefinition } from '../../types/api-types'

interface ModuleRow extends StackModuleEntry {
  _key: string
}

export function StackComposerPage() {
  const [stackName, setStackName] = useState('')
  const [stackDesc, setStackDesc] = useState('')
  const [modules, setModules] = useState<ModuleRow[]>([])
  const [previewHcl, setPreviewHcl] = useState<Record<string, string> | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const { data: registryModules = [] } = useRegistryModules(searchQuery || undefined)
  const compose = useComposeProject()
  const saveTemplate = useCreateStackTemplate()

  function addModule(source: string, version: string, name: string) {
    const safeName = name.replace(/[^a-z0-9_]/gi, '_').toLowerCase()
    setModules(prev => [
      ...prev,
      { _key: crypto.randomUUID(), module_id: '', alias: safeName, name: safeName, source, version, variables: {}, depends_on: [] },
    ])
  }

  function removeModule(key: string) {
    setModules(prev => prev.filter(m => m._key !== key))
  }

  function updateModule(key: string, patch: Partial<StackModuleEntry>) {
    setModules(prev => prev.map(m => m._key === key ? { ...m, ...patch } : m))
  }

  function buildDefinition(): StackDefinition {
    return {
      modules: modules.map(({ _key: _, ...m }) => m),
    }
  }

  async function handlePreview() {
    setError('')
    if (modules.length === 0) { setError('Add at least one module'); return }
    try {
      const result = await compose.mutateAsync({
        project_id: `preview-${Date.now()}`,
        stack_definition: buildDefinition(),
      })
      setPreviewHcl(result.generated_files ?? null)
      setWarnings(result.warnings ?? [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Compose failed')
    }
  }

  async function handleSave() {
    setError('')
    if (!stackName.trim()) { setError('Stack name is required'); return }
    if (modules.length === 0) { setError('Add at least one module'); return }
    try {
      await saveTemplate.mutateAsync({
        name: stackName.trim(),
        description: stackDesc,
        definition: buildDefinition(),
        tags: [],
      })
      setError('')
      alert('Stack template saved!')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
          <Layers size={20} className="text-blue-400" /> Stack Composer
        </h1>
        <p className="text-sm text-zinc-400 mt-0.5">
          Compose registry modules into a deployable Terraform stack
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: module picker */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-zinc-300">Registry Modules</h2>
          <input
            type="text"
            placeholder="Search modules..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
          />
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {registryModules.map(mod => (
              <div
                key={mod.id}
                className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded-lg"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-zinc-200 truncate">{mod.name}</p>
                  <p className="text-xs text-zinc-500">{mod.namespace}/{mod.provider}</p>
                </div>
                <button
                  onClick={() => addModule(
                    `${mod.namespace}/${mod.name}/${mod.provider}`,
                    mod.latest_version ?? '1.0.0',
                    mod.name,
                  )}
                  className="ml-2 p-1 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 rounded"
                >
                  <Plus size={16} />
                </button>
              </div>
            ))}
            {registryModules.length === 0 && (
              <p className="text-xs text-zinc-600 text-center py-4">No modules found</p>
            )}
          </div>
        </div>

        {/* Center: stack builder */}
        <div className="lg:col-span-2 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-zinc-400">Stack name</label>
              <input
                value={stackName}
                onChange={e => setStackName(e.target.value)}
                placeholder="my-stack"
                className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-zinc-400">Description</label>
              <input
                value={stackDesc}
                onChange={e => setStackDesc(e.target.value)}
                placeholder="Optional description"
                className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Module rows */}
          <div className="space-y-2">
            {modules.length === 0 && (
              <div className="border-2 border-dashed border-zinc-800 rounded-lg p-8 text-center text-zinc-600 text-sm">
                Add modules from the left panel
              </div>
            )}
            {modules.map((mod, idx) => (
              <ModuleRow
                key={mod._key}
                mod={mod}
                index={idx}
                onUpdate={patch => updateModule(mod._key, patch)}
                onRemove={() => removeModule(mod._key)}
              />
            ))}
          </div>

          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="space-y-1">
              {warnings.map((w, i) => (
                <p key={i} className="text-xs text-yellow-400 bg-yellow-500/10 px-3 py-1.5 rounded">{w}</p>
              ))}
            </div>
          )}
          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handlePreview}
              disabled={compose.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 text-sm rounded transition-colors disabled:opacity-50"
            >
              <Eye size={14} /> Preview HCL
            </button>
            <button
              onClick={handleSave}
              disabled={saveTemplate.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded transition-colors disabled:opacity-50"
            >
              <Save size={14} /> Save Template
            </button>
          </div>

          {/* HCL preview */}
          {previewHcl && (
            <div className="space-y-3">
              {Object.entries(previewHcl).map(([filename, content]) => (
                <div key={filename}>
                  <p className="text-xs font-medium text-zinc-400 mb-1">{filename}</p>
                  <pre className="text-xs text-zinc-300 bg-zinc-900 border border-zinc-800 rounded p-3 overflow-x-auto max-h-64 whitespace-pre">
                    {content}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Module row editor
// ---------------------------------------------------------------------------

function ModuleRow({
  mod, index, onUpdate, onRemove,
}: {
  mod: StackModuleEntry & { _key: string }
  index: number
  onUpdate: (patch: Partial<StackModuleEntry>) => void
  onRemove: () => void
}) {
  return (
    <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500">Module {index + 1}</span>
        <button onClick={onRemove} className="text-zinc-600 hover:text-red-400">
          <Trash2 size={13} />
        </button>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-xs text-zinc-500">Local name</label>
          <input
            value={mod.name ?? mod.alias}
            onChange={e => onUpdate({ name: e.target.value })}
            className="w-full px-2 py-1 bg-zinc-950 border border-zinc-700 rounded text-xs text-zinc-200 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label className="text-xs text-zinc-500">Source</label>
          <input
            value={mod.source ?? ''}
            onChange={e => onUpdate({ source: e.target.value })}
            className="w-full px-2 py-1 bg-zinc-950 border border-zinc-700 rounded text-xs text-zinc-200 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label className="text-xs text-zinc-500">Version</label>
          <input
            value={mod.version}
            onChange={e => onUpdate({ version: e.target.value })}
            className="w-full px-2 py-1 bg-zinc-950 border border-zinc-700 rounded text-xs text-zinc-200 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>
    </div>
  )
}
