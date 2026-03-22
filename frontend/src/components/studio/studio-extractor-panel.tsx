// Extractor mode panel — paste raw HCL → AI extracts parameterized Jinja2 template.
// Left panel in AI Studio two-panel layout.

import { useState } from 'react'
import { StudioChatPanel } from './studio-chat-panel'
import type { StudioTemplate, StudioStatus, ChatMessage } from '../../types/studio-types'

interface StudioExtractorPanelProps {
  template: StudioTemplate | null
  status: StudioStatus
  error: string | null
  chatHistory: ChatMessage[]
  onExtract: (hclCode: string, templateName?: string) => void
  onRefine: (refinement: string) => void
}

export function StudioExtractorPanel({
  template,
  status,
  error,
  chatHistory,
  onExtract,
  onRefine,
}: StudioExtractorPanelProps) {
  const [hclCode, setHclCode] = useState('')
  const [templateName, setTemplateName] = useState('')

  const handleExtract = () => {
    if (!hclCode.trim()) return
    onExtract(hclCode, templateName.trim() || undefined)
  }

  const isWorking = status === 'extracting' || status === 'refining'

  return (
    <div className="flex flex-col gap-5">
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-3">Paste Raw HCL</h2>
        <textarea
          value={hclCode}
          onChange={e => setHclCode(e.target.value)}
          placeholder={'resource "aws_instance" "web" {\n  ami           = "ami-0c02fb55956c7d316"\n  instance_type = "t3.micro"\n  ...\n}'}
          rows={10}
          disabled={isWorking}
          className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                     text-zinc-100 text-xs font-mono resize-none placeholder-zinc-500
                     focus:outline-none focus:border-blue-500 disabled:opacity-50"
        />

        {/* Optional template name */}
        <div className="mt-3">
          <label className="text-zinc-400 text-xs font-medium block mb-1.5">
            Template Name <span className="text-zinc-600">(optional)</span>
          </label>
          <input
            value={templateName}
            onChange={e => setTemplateName(e.target.value)}
            placeholder="e.g. aws/ec2-web-server"
            disabled={isWorking}
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                       text-zinc-100 text-sm placeholder-zinc-500
                       focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
        </div>

        <button
          onClick={handleExtract}
          disabled={isWorking || !hclCode.trim()}
          className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                     text-white text-sm rounded font-medium transition-colors"
        >
          {isWorking ? 'Extracting...' : template ? 'Re-extract' : 'Extract Template'}
        </button>
      </section>

      {/* Chat refinement (after extraction) */}
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
