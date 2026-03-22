// Banner shown on project detail when registry module upgrades are available

import { ArrowUpCircle, X } from 'lucide-react'
import { useState } from 'react'
import { useModuleUpgrades } from '../../hooks/use-stacks'
import type { UpgradeInfo } from '../../types/api-types'

interface Props {
  projectId: string
}

export function ModuleUpgradeBanner({ projectId }: Props) {
  const { data: upgrades = [], isLoading } = useModuleUpgrades(projectId)
  const [dismissed, setDismissed] = useState(false)

  if (isLoading || dismissed || upgrades.length === 0) return null

  return (
    <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
      <ArrowUpCircle size={18} className="text-blue-400 shrink-0 mt-0.5" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-blue-300">
          {upgrades.length} module upgrade{upgrades.length > 1 ? 's' : ''} available
        </p>
        <div className="mt-2 space-y-1">
          {upgrades.map(u => (
            <UpgradeRow key={u.module_name} upgrade={u} />
          ))}
        </div>
      </div>

      <button
        onClick={() => setDismissed(true)}
        className="text-zinc-500 hover:text-zinc-300 shrink-0"
        aria-label="Dismiss upgrade banner"
      >
        <X size={16} />
      </button>
    </div>
  )
}

function UpgradeRow({ upgrade }: { upgrade: UpgradeInfo }) {
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-400">
      <span className="font-mono text-zinc-300">{upgrade.module_name}</span>
      <span className="text-zinc-600">·</span>
      <span>
        <span className="text-zinc-500 line-through">v{upgrade.current_version}</span>
        <span className="mx-1 text-zinc-600">→</span>
        <span className="text-green-400 font-medium">v{upgrade.latest_version}</span>
      </span>
      <span className="text-zinc-600">·</span>
      <span className="text-zinc-500 font-mono truncate max-w-xs">{upgrade.source}</span>
    </div>
  )
}
