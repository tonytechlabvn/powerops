// Outputs table for module documentation

import type { OutputDoc } from '../../types/api-types'

interface Props {
  outputs: OutputDoc[]
}

export function ModuleOutputsTable({ outputs }: Props) {
  if (outputs.length === 0) {
    return <p className="text-sm text-zinc-500 italic">No outputs defined.</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/50">
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Name</th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Description</th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Value expression</th>
          </tr>
        </thead>
        <tbody>
          {outputs.map(o => (
            <tr key={o.name} className="border-b border-zinc-800/50 hover:bg-zinc-800/20">
              <td className="px-4 py-2.5 font-mono text-xs text-zinc-200 whitespace-nowrap">
                {o.name}
              </td>
              <td className="px-4 py-2.5 text-zinc-400 max-w-xs">
                {o.description || <span className="text-zinc-600 italic">—</span>}
              </td>
              <td className="px-4 py-2.5 font-mono text-xs text-zinc-500 max-w-xs truncate">
                {o.value || <span className="text-zinc-600 italic">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
