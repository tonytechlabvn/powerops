// Variable Sets management page — list sidebar + detail panel.
// Route: /variable-sets

import { useEffect, useState } from 'react'
import { Plus, Globe, ChevronRight, Tag } from 'lucide-react'
import { useVariableSets } from '../../hooks/use-variable-sets'
import { VariableSetDetailPanel } from './variable-set-detail-panel'
import { cn } from '../../lib/utils'
import type { VariableSet, VariableSetVariable } from '../../types/api-types'

// ---------------------------------------------------------------------------
// Create set inline form
// ---------------------------------------------------------------------------

interface CreateSetFormProps {
  onCreate: (name: string, desc: string, isGlobal: boolean) => Promise<void>
  onCancel: () => void
  isLoading: boolean
}

function CreateSetForm({ onCreate, onCancel, isLoading }: CreateSetFormProps) {
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [isGlobal, setIsGlobal] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    await onCreate(name.trim(), desc, isGlobal)
  }

  return (
    <form onSubmit={handleSubmit} className="p-3 border-b border-zinc-800 space-y-2">
      <input
        autoFocus value={name} onChange={e => setName(e.target.value)}
        placeholder="Set name" required
        className="w-full text-sm bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200 placeholder-zinc-600 outline-none focus:border-blue-500"
      />
      <input
        value={desc} onChange={e => setDesc(e.target.value)}
        placeholder="Description (optional)"
        className="w-full text-sm bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200 placeholder-zinc-600 outline-none focus:border-blue-500"
      />
      <label className="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer">
        <input type="checkbox" checked={isGlobal} onChange={e => setIsGlobal(e.target.checked)} className="accent-blue-500" />
        Global (auto-applied to all workspaces)
      </label>
      <div className="flex gap-2">
        <button type="submit" disabled={isLoading || !name.trim()}
          className="flex-1 py-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded">
          Create
        </button>
        <button type="button" onClick={onCancel}
          className="flex-1 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded">
          Cancel
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Set list sidebar item
// ---------------------------------------------------------------------------

interface SetListItemProps {
  vs: VariableSet
  isSelected: boolean
  onSelect: () => void
}

function SetListItem({ vs, isSelected, onSelect }: SetListItemProps) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full flex items-center gap-2 px-3 py-2 text-left text-sm border-b border-zinc-800/50 transition-colors',
        isSelected ? 'bg-blue-600/10 text-blue-300' : 'text-zinc-300 hover:bg-zinc-800',
      )}
    >
      {vs.is_global && <Globe size={12} className="text-green-400 shrink-0" />}
      <span className="flex-1 truncate">{vs.name}</span>
      <span className="text-xs text-zinc-600">{vs.variable_count}</span>
      <ChevronRight size={12} className="text-zinc-700 shrink-0" />
    </button>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function VariableSetsPage() {
  const vs = useVariableSets()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<VariableSet | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => { vs.listSets() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectSet = async (id: string) => {
    setSelectedId(id)
    try {
      setSelectedDetail(await vs.getSet(id))
    } catch {
      setSelectedDetail(null)
    }
  }

  const handleCreate = async (name: string, desc: string, isGlobal: boolean) => {
    await vs.createSet(name, desc, isGlobal)
    setShowCreate(false)
  }

  const handleDeleteSet = async (id: string) => {
    if (!window.confirm('Delete this variable set and all its variables?')) return
    await vs.deleteSet(id)
    if (selectedId === id) { setSelectedId(null); setSelectedDetail(null) }
  }

  const handleAddVariable = async (vsId: string, v: Omit<VariableSetVariable, 'id' | 'variable_set_id'>) => {
    await vs.setVariable(vsId, v)
    const updated = await vs.getSet(vsId)
    setSelectedDetail(updated)
    await vs.listSets()
  }

  const handleDeleteVariable = async (vsId: string, varId: string) => {
    if (!window.confirm('Delete this variable?')) return
    await vs.deleteVariable(vsId, varId)
    const updated = await vs.getSet(vsId)
    setSelectedDetail(updated)
    await vs.listSets()
  }

  return (
    <div className="flex h-full overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Left: set list sidebar */}
      <div className="w-64 shrink-0 flex flex-col border-r border-zinc-800 bg-zinc-900">
        {/* Sidebar header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Tag size={15} className="text-blue-400" />
            <span className="text-sm font-semibold">Variable Sets</span>
          </div>
          <button
            onClick={() => setShowCreate(s => !s)}
            className="p-1 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 rounded"
            title="New variable set"
          >
            <Plus size={15} />
          </button>
        </div>

        {showCreate && (
          <CreateSetForm
            onCreate={handleCreate}
            onCancel={() => setShowCreate(false)}
            isLoading={vs.isLoading}
          />
        )}

        {/* Set list */}
        <div className="flex-1 overflow-y-auto py-1">
          {vs.isLoading && vs.variableSets.length === 0 ? (
            <div className="px-4 py-4 text-xs text-zinc-600 text-center">Loading...</div>
          ) : vs.variableSets.length === 0 ? (
            <div className="px-4 py-6 text-xs text-zinc-600 text-center">No variable sets yet.</div>
          ) : (
            vs.variableSets.map(s => (
              <SetListItem
                key={s.id}
                vs={s}
                isSelected={selectedId === s.id}
                onSelect={() => handleSelectSet(s.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Right: detail panel */}
      <div className="flex-1 overflow-hidden">
        {selectedDetail ? (
          <VariableSetDetailPanel
            vs={selectedDetail}
            onDeleteVariable={handleDeleteVariable}
            onAddVariable={handleAddVariable}
            onDeleteSet={handleDeleteSet}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-zinc-600 gap-2">
            <Tag size={32} />
            <span className="text-sm">Select a variable set to view and manage variables</span>
          </div>
        )}
      </div>
    </div>
  )
}
