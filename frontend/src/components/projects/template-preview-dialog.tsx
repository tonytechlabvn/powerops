// Template preview dialog — shows full template detail, variable inputs, and creates project

import { useEffect, useState } from 'react'
import { X, ChevronRight, Box, Variable } from 'lucide-react'
import { apiClient } from '../../services/api-client'

interface TemplateVariable {
  name: string
  type: string
  default: unknown
  description: string
}

interface TemplateModule {
  name: string
  provider: string
  depends_on: string[]
  description: string
}

interface TemplateDetail {
  name: string
  display_name: string
  description: string
  category: string
  complexity: string
  providers: string[]
  tags: string[]
  variables: TemplateVariable[]
  modules: TemplateModule[]
  roles: string[]
  outputs: Array<{ name: string; module: string; description: string }>
}

interface Props {
  templateName: string
  onClose: () => void
  onCreated: () => void
}

const PROVIDER_COLOR: Record<string, string> = {
  aws:     'bg-orange-500/20 text-orange-400',
  proxmox: 'bg-purple-500/20 text-purple-400',
}

export function TemplatePreviewDialog({ templateName, onClose, onCreated }: Props) {
  const [detail, setDetail]       = useState<TemplateDetail | null>(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')
  const [variables, setVariables] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    apiClient
      .get<TemplateDetail>(`/api/project-templates/${templateName}`)
      .then(data => {
        setDetail(data)
        // Pre-fill variable defaults
        const defaults: Record<string, string> = {}
        for (const v of data.variables) {
          defaults[v.name] = v.default !== null && v.default !== undefined
            ? String(v.default)
            : ''
        }
        setVariables(defaults)
      })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load template'))
      .finally(() => setLoading(false))
  }, [templateName])

  function setVar(name: string, value: string) {
    setVariables(prev => ({ ...prev, [name]: value }))
  }

  async function handleCreate() {
    if (!detail) return
    setSubmitError(null)
    setSubmitting(true)
    try {
      await apiClient.post(`/api/project-templates/${templateName}/create`, {
        project_name: projectName.trim(),
        variables,
      })
      onCreated()
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800 shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-zinc-100">
              {loading ? 'Loading...' : detail?.display_name}
            </h2>
            {detail && (
              <p className="text-xs text-zinc-500 mt-0.5">{detail.description}</p>
            )}
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 shrink-0 ml-4">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-5 space-y-5">
          {loading && <p className="text-zinc-500 text-sm text-center py-8">Loading template...</p>}
          {!loading && error && <p className="text-red-400 text-sm">{error}</p>}

          {!loading && detail && (
            <>
              {/* Providers + tags */}
              <div className="flex flex-wrap gap-2">
                {detail.providers.map(p => (
                  <span key={p} className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROVIDER_COLOR[p] ?? 'bg-zinc-700 text-zinc-400'}`}>
                    {p.toUpperCase()}
                  </span>
                ))}
                <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-700/60 text-zinc-400 font-medium">
                  {detail.complexity}
                </span>
                {detail.tags.map(tag => (
                  <span key={tag} className="text-xs bg-zinc-800 text-zinc-500 rounded px-1.5 py-0.5">{tag}</span>
                ))}
              </div>

              {/* Modules structure */}
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Box size={13} className="text-zinc-400" />
                  <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
                    Modules ({detail.modules.length})
                  </span>
                </div>
                <div className="space-y-1.5">
                  {detail.modules.map((mod, idx) => (
                    <div key={mod.name} className="bg-zinc-800 rounded px-3 py-2">
                      <div className="flex items-center gap-2">
                        {idx > 0 && mod.depends_on.length > 0 && (
                          <ChevronRight size={12} className="text-zinc-600 shrink-0" />
                        )}
                        <span className="text-zinc-200 text-xs font-mono">{mod.name}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${PROVIDER_COLOR[mod.provider] ?? 'bg-zinc-700 text-zinc-400'}`}>
                          {mod.provider}
                        </span>
                        {mod.depends_on.length > 0 && (
                          <span className="text-zinc-600 text-xs">
                            depends on: {mod.depends_on.join(', ')}
                          </span>
                        )}
                      </div>
                      {mod.description && (
                        <p className="text-zinc-500 text-xs mt-1 leading-relaxed">{mod.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Project name */}
              <div>
                <label className="block text-sm text-zinc-400 mb-1">
                  Project Name
                  <span className="text-zinc-600 ml-1">(leave blank to use template name)</span>
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={e => setProjectName(e.target.value)}
                  placeholder={detail.name}
                  className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm placeholder-zinc-600 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Variables */}
              {detail.variables.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Variable size={13} className="text-zinc-400" />
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
                      Variables
                    </span>
                  </div>
                  <div className="space-y-2.5">
                    {detail.variables.map(v => (
                      <div key={v.name}>
                        <label className="block text-xs text-zinc-400 mb-1">
                          <span className="font-mono text-zinc-300">{v.name}</span>
                          <span className="text-zinc-600 ml-1.5">({v.type})</span>
                          {v.description && (
                            <span className="text-zinc-500 ml-1.5">— {v.description}</span>
                          )}
                        </label>
                        <input
                          type="text"
                          value={variables[v.name] ?? ''}
                          onChange={e => setVar(v.name, e.target.value)}
                          className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-1.5 text-sm font-mono placeholder-zinc-600 focus:outline-none focus:border-blue-500"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {submitError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded px-3 py-2">
                  {submitError}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {!loading && detail && (
          <div className="flex justify-end gap-3 px-5 py-4 border-t border-zinc-800 shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={submitting}
              className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 disabled:cursor-not-allowed text-white font-medium rounded transition-colors"
            >
              {submitting ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
