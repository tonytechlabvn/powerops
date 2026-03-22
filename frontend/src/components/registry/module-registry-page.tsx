// Module Registry page — browse, search, and publish Terraform modules

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Package, Plus, Tag, ChevronRight } from 'lucide-react'
import { useRegistryModules } from '../../hooks/use-module-registry'
import { PublishModuleDialog } from './publish-module-dialog'
import type { RegistryModule } from '../../types/api-types'

export function ModuleRegistryPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [provider, setProvider] = useState('')
  const [showPublish, setShowPublish] = useState(false)

  const { data: modules = [], isLoading, error } = useRegistryModules(
    search || undefined,
    provider || undefined,
  )

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Module Registry</h1>
          <p className="text-sm text-zinc-400 mt-0.5">
            Private Terraform modules for your organization
          </p>
        </div>
        <button
          onClick={() => setShowPublish(true)}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md transition-colors"
        >
          <Plus size={15} />
          Publish Module
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            placeholder="Search modules..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        <select
          value={provider}
          onChange={e => setProvider(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm text-zinc-300 focus:outline-none focus:border-blue-500"
        >
          <option value="">All providers</option>
          <option value="aws">AWS</option>
          <option value="azurerm">Azure</option>
          <option value="google">GCP</option>
          <option value="generic">Generic</option>
        </select>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="text-sm text-zinc-400">Loading modules...</div>
      )}
      {error && (
        <div className="text-sm text-red-400">Failed to load modules.</div>
      )}
      {!isLoading && modules.length === 0 && (
        <div className="text-center py-16 text-zinc-500">
          <Package size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No modules published yet.</p>
          <button
            onClick={() => setShowPublish(true)}
            className="mt-3 text-sm text-blue-400 hover:text-blue-300"
          >
            Publish your first module
          </button>
        </div>
      )}

      {/* Module grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map(mod => (
          <ModuleCard
            key={mod.id}
            module={mod}
            onClick={() => navigate(`/registry/${mod.id}`)}
          />
        ))}
      </div>

      {showPublish && (
        <PublishModuleDialog onClose={() => setShowPublish(false)} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Module card
// ---------------------------------------------------------------------------

function ModuleCard({ module: mod, onClick }: { module: RegistryModule; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-left p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-600 transition-colors group"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Package size={16} className="text-blue-400 shrink-0" />
          <span className="font-medium text-zinc-100 truncate">{mod.name}</span>
        </div>
        <ChevronRight
          size={15}
          className="text-zinc-600 group-hover:text-zinc-400 shrink-0 mt-0.5"
        />
      </div>

      <p className="mt-1 text-xs text-zinc-500">
        {mod.namespace} / {mod.provider}
      </p>

      {mod.description && (
        <p className="mt-2 text-sm text-zinc-400 line-clamp-2">{mod.description}</p>
      )}

      <div className="mt-3 flex items-center gap-2 flex-wrap">
        {mod.latest_version && (
          <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded-full">
            v{mod.latest_version}
          </span>
        )}
        <span className="px-2 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded-full">
          {mod.version_count ?? 0} version{mod.version_count !== 1 ? 's' : ''}
        </span>
        {(mod.tags ?? []).slice(0, 2).map(tag => (
          <span
            key={tag}
            className="flex items-center gap-1 px-2 py-0.5 bg-zinc-800 text-zinc-500 text-xs rounded-full"
          >
            <Tag size={10} />
            {tag}
          </span>
        ))}
      </div>
    </button>
  )
}
