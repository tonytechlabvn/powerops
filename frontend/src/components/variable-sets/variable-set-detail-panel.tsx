// Detail panel for a single variable set: variable list + add variable form.
// Used by variable-sets-page.tsx as the right-side panel.

import { useState } from 'react'
import { Trash2, Globe, Lock, Unlock } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { VariableSet, VariableSetVariable } from '../../types/api-types'

// ---------------------------------------------------------------------------
// Variable row
// ---------------------------------------------------------------------------

interface VariableRowProps {
  variable: VariableSetVariable
  onDelete: (id: string) => void
}

function VariableRow({ variable, onDelete }: VariableRowProps) {
  const [revealed, setRevealed] = useState(false)

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-zinc-800 text-sm group">
      <span className="font-mono text-zinc-200 w-40 truncate">{variable.key}</span>
      <span className={cn(
        'flex-1 font-mono truncate',
        variable.is_sensitive ? 'text-zinc-600' : 'text-zinc-400',
      )}>
        {variable.is_sensitive
          ? (revealed ? variable.value : '••••••••')
          : (variable.value || <span className="text-zinc-700 italic">empty</span>)
        }
      </span>

      <div className="flex items-center gap-2 ml-auto shrink-0">
        <span className={cn(
          'text-xs px-1.5 py-0.5 rounded',
          variable.category === 'env'
            ? 'bg-purple-500/10 text-purple-400'
            : 'bg-blue-500/10 text-blue-400',
        )}>
          {variable.category === 'env' ? 'env' : 'tf'}
        </span>

        {variable.is_hcl && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-400">HCL</span>
        )}

        {variable.is_sensitive && (
          <button
            onClick={() => setRevealed(r => !r)}
            className="text-zinc-600 hover:text-zinc-400 p-0.5 rounded"
            title={revealed ? 'Hide value' : 'Reveal value'}
          >
            {revealed ? <Lock size={12} /> : <Unlock size={12} />}
          </button>
        )}

        <button
          onClick={() => onDelete(variable.id)}
          className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 p-0.5 rounded transition-opacity"
          title="Delete variable"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Add variable inline form
// ---------------------------------------------------------------------------

interface AddVariableFormProps {
  onAdd: (v: Omit<VariableSetVariable, 'id' | 'variable_set_id'>) => Promise<void>
}

function AddVariableForm({ onAdd }: AddVariableFormProps) {
  const [key, setKey] = useState('')
  const [value, setValue] = useState('')
  const [category, setCategory] = useState<'terraform' | 'env'>('terraform')
  const [isSensitive, setIsSensitive] = useState(false)
  const [isHcl, setIsHcl] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.trim()) return
    setSubmitting(true)
    try {
      await onAdd({ key: key.trim(), value, category, is_sensitive: isSensitive, is_hcl: isHcl, description: '' })
      setKey(''); setValue(''); setIsSensitive(false); setIsHcl(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}
      className="flex flex-wrap items-center gap-2 px-4 py-3 border-t border-zinc-800 bg-zinc-900/50">
      <input
        value={key} onChange={e => setKey(e.target.value)}
        placeholder="KEY" required
        className="font-mono text-sm bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200 placeholder-zinc-600 w-36 outline-none focus:border-blue-500"
      />
      <input
        value={value} onChange={e => setValue(e.target.value)}
        placeholder="value" type={isSensitive ? 'password' : 'text'}
        className="font-mono text-sm bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-200 placeholder-zinc-600 flex-1 min-w-28 outline-none focus:border-blue-500"
      />
      <select value={category} onChange={e => setCategory(e.target.value as 'terraform' | 'env')}
        className="text-xs bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300 outline-none focus:border-blue-500">
        <option value="terraform">Terraform</option>
        <option value="env">Environment</option>
      </select>
      <label className="flex items-center gap-1 text-xs text-zinc-400 cursor-pointer">
        <input type="checkbox" checked={isSensitive} onChange={e => setIsSensitive(e.target.checked)} className="accent-blue-500" />
        Sensitive
      </label>
      <label className="flex items-center gap-1 text-xs text-zinc-400 cursor-pointer">
        <input type="checkbox" checked={isHcl} onChange={e => setIsHcl(e.target.checked)} className="accent-blue-500" />
        HCL
      </label>
      <button type="submit" disabled={submitting || !key.trim()}
        className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded">
        Add
      </button>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Exported detail panel
// ---------------------------------------------------------------------------

interface VariableSetDetailPanelProps {
  vs: VariableSet
  onDeleteVariable: (vsId: string, varId: string) => Promise<void>
  onAddVariable: (vsId: string, v: Omit<VariableSetVariable, 'id' | 'variable_set_id'>) => Promise<void>
  onDeleteSet: (id: string) => void
}

export function VariableSetDetailPanel({
  vs, onDeleteVariable, onAddVariable, onDeleteSet,
}: VariableSetDetailPanelProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-zinc-100 truncate">{vs.name}</h2>
            {vs.is_global && (
              <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-green-500/10 text-green-400">
                <Globe size={10} /> Global
              </span>
            )}
          </div>
          {vs.description && (
            <p className="text-xs text-zinc-500 mt-0.5 truncate">{vs.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span>{vs.variable_count} var{vs.variable_count !== 1 ? 's' : ''}</span>
          <span>·</span>
          <span>{vs.workspace_count} workspace{vs.workspace_count !== 1 ? 's' : ''}</span>
        </div>
        <button onClick={() => onDeleteSet(vs.id)}
          className="text-zinc-600 hover:text-red-400 p-1 rounded" title="Delete variable set">
          <Trash2 size={15} />
        </button>
      </div>

      {/* Column headers */}
      <div className="flex items-center gap-3 px-4 py-1.5 border-b border-zinc-800 text-xs text-zinc-600 uppercase tracking-wide">
        <span className="w-40">Key</span>
        <span className="flex-1">Value</span>
        <span className="ml-auto">Type</span>
      </div>

      {/* Variables list */}
      <div className="flex-1 overflow-y-auto">
        {vs.variables.length === 0 ? (
          <div className="px-4 py-6 text-sm text-zinc-600 text-center">No variables yet. Add one below.</div>
        ) : (
          vs.variables.map(v => (
            <VariableRow key={v.id} variable={v} onDelete={id => onDeleteVariable(vs.id, id)} />
          ))
        )}
      </div>

      {/* Add variable form */}
      <AddVariableForm onAdd={v => onAddVariable(vs.id, v)} />
    </div>
  )
}
