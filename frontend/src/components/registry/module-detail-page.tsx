// Module detail page — README, variables, outputs, resources, usage example, download

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Package, Copy, Check, ChevronDown } from 'lucide-react'
import { useRegistryModule, useModuleDocs } from '../../hooks/use-module-registry'
import { ModuleVariablesTable } from './module-variables-table'
import { ModuleOutputsTable } from './module-outputs-table'

type Tab = 'readme' | 'inputs' | 'outputs' | 'resources' | 'usage'

export function ModuleDetailPage() {
  const { moduleId } = useParams<{ moduleId: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('readme')
  const [selectedVersion, setSelectedVersion] = useState<string>('')
  const [copied, setCopied] = useState(false)

  const { data: module, isLoading } = useRegistryModule(moduleId ?? '')
  const { data: docs } = useModuleDocs(moduleId ?? '', selectedVersion || undefined)

  if (isLoading) {
    return <div className="p-6 text-sm text-zinc-400">Loading...</div>
  }
  if (!module) {
    return <div className="p-6 text-sm text-red-400">Module not found.</div>
  }

  const versions = module.versions ?? []
  const activeVersion = selectedVersion || module.latest_version || ''
  const usageSnippet = docs?.usage_example ?? generateUsageSnippet(module, activeVersion)

  function copyUsage() {
    navigator.clipboard.writeText(usageSnippet)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleDownload() {
    if (!activeVersion || !module) return
    window.open(`/api/registry/modules/${module.id}/versions/${activeVersion}/download`, '_blank')
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Back + header */}
      <button
        onClick={() => navigate('/registry')}
        className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-100"
      >
        <ArrowLeft size={14} /> Registry
      </button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Package size={18} className="text-blue-400" />
            <h1 className="text-xl font-semibold text-zinc-100">{module.name}</h1>
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            {module.namespace} / {module.provider}
          </p>
          {module.description && (
            <p className="text-sm text-zinc-400 mt-2">{module.description}</p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Version selector */}
          <div className="relative">
            <select
              value={activeVersion}
              onChange={e => setSelectedVersion(e.target.value)}
              className="appearance-none pl-3 pr-7 py-1.5 bg-zinc-900 border border-zinc-700 rounded text-sm text-zinc-200 focus:outline-none focus:border-blue-500"
            >
              {versions.map(v => (
                <option key={v.id} value={v.version}>v{v.version}</option>
              ))}
            </select>
            <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
          </div>
          <button
            onClick={handleDownload}
            disabled={!activeVersion}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 text-sm rounded transition-colors disabled:opacity-40"
          >
            <Download size={14} /> Download
          </button>
        </div>
      </div>

      {/* Usage snippet */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Usage</span>
          <button
            onClick={copyUsage}
            className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300"
          >
            {copied ? <Check size={13} className="text-green-400" /> : <Copy size={13} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <pre className="text-xs text-zinc-300 overflow-x-auto whitespace-pre">{usageSnippet}</pre>
      </div>

      {/* Tabs */}
      <div className="border-b border-zinc-800">
        <nav className="flex gap-1">
          {(['readme', 'inputs', 'outputs', 'resources', 'usage'] as Tab[]).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {tab === 'readme' && (
          <ReadmeTab content={docs?.readme ?? ''} />
        )}
        {tab === 'inputs' && (
          <ModuleVariablesTable variables={docs?.variables ?? []} />
        )}
        {tab === 'outputs' && (
          <ModuleOutputsTable outputs={docs?.outputs ?? []} />
        )}
        {tab === 'resources' && (
          <ResourcesTab resources={docs?.resources ?? []} />
        )}
        {tab === 'usage' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <pre className="text-sm text-zinc-300 overflow-x-auto whitespace-pre">{usageSnippet}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ReadmeTab({ content }: { content: string }) {
  if (!content) {
    return <p className="text-sm text-zinc-500 italic">No README available for this module.</p>
  }
  // Simple pre-rendered markdown display (plain text fallback without react-markdown dep)
  return (
    <div className="prose prose-invert prose-sm max-w-none">
      <pre className="whitespace-pre-wrap text-sm text-zinc-300 bg-zinc-900 border border-zinc-800 rounded-lg p-4 overflow-x-auto">
        {content}
      </pre>
    </div>
  )
}

function ResourcesTab({ resources }: { resources: Array<{ type: string; name: string; provider?: string }> }) {
  if (resources.length === 0) {
    return <p className="text-sm text-zinc-500 italic">No resources detected.</p>
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/50">
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Type</th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Name</th>
            <th className="text-left px-4 py-2.5 text-zinc-400 font-medium">Provider</th>
          </tr>
        </thead>
        <tbody>
          {resources.map((r, i) => (
            <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
              <td className="px-4 py-2.5 text-zinc-300 font-mono text-xs">{r.type}</td>
              <td className="px-4 py-2.5 text-zinc-300">{r.name}</td>
              <td className="px-4 py-2.5 text-zinc-500">{r.provider}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function generateUsageSnippet(module: { name: string; namespace: string; provider: string }, version: string): string {
  return [
    `module "${module.name}" {`,
    `  source  = "powerops.tonytechlab.com/${module.namespace}/${module.name}/${module.provider}"`,
    version ? `  version = "${version}"` : '',
    `}`,
  ].filter(Boolean).join('\n')
}
