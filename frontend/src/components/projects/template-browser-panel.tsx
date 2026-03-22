// Template browser panel — card grid of available project templates with category/provider filters

import { useEffect, useState } from 'react'
import { Layers, Filter } from 'lucide-react'
import { apiClient } from '../../services/api-client'

interface TemplateInfo {
  name: string
  display_name: string
  description: string
  category: string
  complexity: string
  providers: string[]
  tags: string[]
  module_count: number
}

interface Props {
  onSelect: (name: string) => void
}

const COMPLEXITY_COLOR: Record<string, string> = {
  beginner:     'bg-green-500/20 text-green-400',
  intermediate: 'bg-yellow-500/20 text-yellow-400',
  advanced:     'bg-red-500/20 text-red-400',
}

const CATEGORY_LABELS: Record<string, string> = {
  'hybrid-cloud': 'Hybrid Cloud',
  'web-app':      'Web App',
  'static-site':  'Static Site',
  'database':     'Database',
  'compute':      'Compute',
  'other':        'Other',
}

export function TemplateBrowserPanel({ onSelect }: Props) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [filterCategory, setFilterCategory] = useState('')
  const [filterProvider, setFilterProvider] = useState('')

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params: Record<string, string> = {}
    if (filterCategory) params.category = filterCategory
    if (filterProvider) params.provider  = filterProvider

    apiClient
      .get<TemplateInfo[]>('/api/project-templates', params)
      .then(setTemplates)
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load templates'))
      .finally(() => setLoading(false))
  }, [filterCategory, filterProvider])

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3 items-center">
        <Filter size={14} className="text-zinc-500 shrink-0" />
        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs rounded px-2 py-1.5 focus:outline-none focus:border-blue-500"
        >
          <option value="">All categories</option>
          {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>
        <select
          value={filterProvider}
          onChange={e => setFilterProvider(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs rounded px-2 py-1.5 focus:outline-none focus:border-blue-500"
        >
          <option value="">All providers</option>
          <option value="aws">AWS</option>
          <option value="proxmox">Proxmox</option>
        </select>
      </div>

      {/* State: loading / error / empty */}
      {loading && (
        <p className="text-zinc-500 text-sm text-center py-8">Loading templates...</p>
      )}
      {!loading && error && (
        <p className="text-red-400 text-sm text-center py-4">{error}</p>
      )}
      {!loading && !error && templates.length === 0 && (
        <p className="text-zinc-500 text-sm text-center py-8">No templates match your filters.</p>
      )}

      {/* Template cards grid */}
      {!loading && !error && templates.length > 0 && (
        <div className="grid grid-cols-1 gap-3">
          {templates.map(tpl => (
            <button
              key={tpl.name}
              onClick={() => onSelect(tpl.name)}
              className="text-left bg-zinc-800 hover:bg-zinc-750 border border-zinc-700 hover:border-blue-500/50 rounded-lg p-4 transition-colors group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <Layers size={16} className="text-blue-400 shrink-0 mt-0.5" />
                  <span className="text-zinc-100 text-sm font-medium truncate group-hover:text-blue-300 transition-colors">
                    {tpl.display_name}
                  </span>
                </div>
                <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${COMPLEXITY_COLOR[tpl.complexity] ?? 'bg-zinc-700 text-zinc-400'}`}>
                  {tpl.complexity}
                </span>
              </div>

              <p className="mt-1.5 text-zinc-400 text-xs leading-relaxed line-clamp-2">
                {tpl.description}
              </p>

              <div className="mt-2.5 flex items-center gap-3 text-xs text-zinc-500">
                <span>{tpl.module_count} module{tpl.module_count !== 1 ? 's' : ''}</span>
                <span className="text-zinc-700">·</span>
                <span>{tpl.providers.join(', ')}</span>
                <span className="text-zinc-700">·</span>
                <span>{CATEGORY_LABELS[tpl.category] ?? tpl.category}</span>
              </div>

              {tpl.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {tpl.tags.slice(0, 5).map(tag => (
                    <span key={tag} className="text-xs bg-zinc-700/60 text-zinc-400 rounded px-1.5 py-0.5">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
