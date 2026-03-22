// Sortable variables table for module documentation

import { useState } from 'react'
import { ArrowUpDown } from 'lucide-react'
import type { VariableDoc } from '../../types/api-types'

interface Props {
  variables: VariableDoc[]
}

type SortKey = 'name' | 'type' | 'required'

export function ModuleVariablesTable({ variables }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('required')
  const [sortAsc, setSortAsc] = useState(false)

  if (variables.length === 0) {
    return <p className="text-sm text-zinc-500 italic">No input variables defined.</p>
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(prev => !prev)
    } else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  const sorted = [...variables].sort((a, b) => {
    let cmp = 0
    if (sortKey === 'name') cmp = a.name.localeCompare(b.name)
    else if (sortKey === 'type') cmp = a.type.localeCompare(b.type)
    else if (sortKey === 'required') cmp = (b.required ? 1 : 0) - (a.required ? 1 : 0)
    return sortAsc ? cmp : -cmp
  })

  function SortHeader({ col, label }: { col: SortKey; label: string }) {
    return (
      <button
        onClick={() => toggleSort(col)}
        className="flex items-center gap-1 text-zinc-400 font-medium hover:text-zinc-200"
      >
        {label}
        <ArrowUpDown size={12} className="opacity-50" />
      </button>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/50">
            <th className="text-left px-4 py-2.5">
              <SortHeader col="name" label="Name" />
            </th>
            <th className="text-left px-4 py-2.5">
              <SortHeader col="type" label="Type" />
            </th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Description</th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Default</th>
            <th className="text-left px-4 py-2.5">
              <SortHeader col="required" label="Required" />
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(v => (
            <tr key={v.name} className="border-b border-zinc-800/50 hover:bg-zinc-800/20">
              <td className="px-4 py-2.5 font-mono text-xs text-zinc-200">{v.name}</td>
              <td className="px-4 py-2.5">
                <TypeBadge type={v.type} />
              </td>
              <td className="px-4 py-2.5 text-zinc-400 max-w-xs">
                <span className="line-clamp-2">{v.description || '—'}</span>
              </td>
              <td className="px-4 py-2.5 font-mono text-xs text-zinc-500">
                {v.default !== null && v.default !== undefined ? String(v.default) : '—'}
              </td>
              <td className="px-4 py-2.5">
                {v.required ? (
                  <span className="px-2 py-0.5 bg-red-500/10 text-red-400 text-xs rounded-full">
                    required
                  </span>
                ) : (
                  <span className="px-2 py-0.5 bg-zinc-800 text-zinc-500 text-xs rounded-full">
                    optional
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    string: 'bg-blue-500/10 text-blue-400',
    number: 'bg-purple-500/10 text-purple-400',
    bool: 'bg-orange-500/10 text-orange-400',
    list: 'bg-green-500/10 text-green-400',
    map: 'bg-teal-500/10 text-teal-400',
    any: 'bg-zinc-700 text-zinc-400',
  }
  const key = Object.keys(colors).find(k => type.startsWith(k)) ?? 'any'
  return (
    <span className={`px-2 py-0.5 text-xs rounded font-mono ${colors[key]}`}>
      {type}
    </span>
  )
}
