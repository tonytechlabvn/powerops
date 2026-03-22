// Creator mode panel — NL description + provider selector + complexity → generate template.
// Left panel in AI Studio two-panel layout.

import { useState } from 'react'
import { StudioChatPanel } from './studio-chat-panel'
import type { StudioTemplate, StudioStatus, ChatMessage } from '../../types/studio-types'

interface StudioCreatorPanelProps {
  template: StudioTemplate | null
  status: StudioStatus
  error: string | null
  chatHistory: ChatMessage[]
  onGenerate: (description: string, providers: string[], complexity: string) => void
  onRefine: (refinement: string) => void
}

const PROVIDERS = ['aws', 'proxmox', 'azurerm', 'google']
const COMPLEXITIES = [
  { value: 'simple', label: 'Simple', hint: 'Single resource, 3-5 variables' },
  { value: 'standard', label: 'Standard', hint: '3-8 resources, comprehensive vars' },
  { value: 'complex', label: 'Complex', hint: 'Multi-resource, auto-mode, scripts' },
]

export function StudioCreatorPanel({
  template,
  status,
  error,
  chatHistory,
  onGenerate,
  onRefine,
}: StudioCreatorPanelProps) {
  const [description, setDescription] = useState('')
  const [selectedProviders, setSelectedProviders] = useState<string[]>(['aws'])
  const [complexity, setComplexity] = useState('standard')

  const toggleProvider = (p: string) => {
    setSelectedProviders(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p],
    )
  }

  const handleGenerate = () => {
    if (!description.trim() || selectedProviders.length === 0) return
    onGenerate(description, selectedProviders, complexity)
  }

  const isWorking = status === 'generating' || status === 'refining'

  return (
    <div className="flex flex-col gap-5">
      {/* Description */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-3">Describe Your Template</h2>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="e.g. WireGuard VPN between AWS EC2 and Proxmox VM with auto key generation..."
          rows={5}
          disabled={isWorking}
          className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                     text-zinc-100 text-sm resize-none placeholder-zinc-500
                     focus:outline-none focus:border-blue-500 disabled:opacity-50"
        />

        {/* Provider selector (multi-select) */}
        <div className="mt-3">
          <label className="text-zinc-400 text-xs font-medium block mb-1.5">Providers</label>
          <div className="flex gap-2 flex-wrap">
            {PROVIDERS.map(p => (
              <button
                key={p}
                onClick={() => toggleProvider(p)}
                disabled={isWorking}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors
                  ${selectedProviders.includes(p)
                    ? 'bg-blue-600 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:text-zinc-200'
                  } disabled:opacity-50`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Complexity selector */}
        <div className="mt-3">
          <label className="text-zinc-400 text-xs font-medium block mb-1.5">Complexity</label>
          <div className="space-y-1.5">
            {COMPLEXITIES.map(c => (
              <button
                key={c.value}
                onClick={() => setComplexity(c.value)}
                disabled={isWorking}
                className={`w-full text-left px-3 py-2 rounded border text-xs transition-colors
                  ${complexity === c.value
                    ? 'border-blue-500 bg-blue-950/30 text-zinc-100'
                    : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600'
                  } disabled:opacity-50`}
              >
                <span className="font-medium">{c.label}</span>
                <span className="text-zinc-500 ml-2">{c.hint}</span>
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isWorking || !description.trim() || selectedProviders.length === 0}
          className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                     text-white text-sm rounded font-medium transition-colors"
        >
          {isWorking ? 'Generating...' : template ? 'Regenerate' : 'Generate Template'}
        </button>
      </section>

      {/* Chat refinement (after generation) */}
      {template && (
        <section className="border-t border-zinc-800 pt-5">
          <StudioChatPanel
            chatHistory={chatHistory}
            status={status}
            onSendRefinement={onRefine}
          />
        </section>
      )}

      {error && <p className="text-red-400 text-xs">{error}</p>}
    </div>
  )
}
