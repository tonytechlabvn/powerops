// Dialog for generating HCL from natural language — streams result, user accepts or discards.

import { useState, useEffect, useRef } from 'react'
import { useAIEditor } from '../../hooks/use-ai-editor'

interface AIGenerateDialogProps {
  workspaceId: string
  currentFile?: string
  currentContent?: string
  onInsert: (code: string) => void
  onClose: () => void
}

const PROVIDERS = ['aws', 'azurerm', 'google', 'proxmox']

// Extract HCL from <terraform>...</terraform> tags, fallback to full text
function extractHCL(text: string): string {
  const match = text.match(/<terraform>([\s\S]*?)<\/terraform>/)
  return match ? match[1].trim() : text.trim()
}

export function AIGenerateDialog({
  workspaceId,
  currentFile,
  currentContent,
  onInsert,
  onClose,
}: AIGenerateDialogProps) {
  const [prompt, setPrompt] = useState('')
  const [provider, setProvider] = useState('aws')
  const { state, generate, reset } = useAIEditor(workspaceId)
  const promptRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    promptRef.current?.focus()
  }, [])

  const handleGenerate = () => {
    if (!prompt.trim()) return
    generate(prompt, currentFile, currentContent, provider)
  }

  const handleInsert = () => {
    const hcl = extractHCL(state.text)
    if (hcl) onInsert(hcl)
    onClose()
  }

  const handleReset = () => {
    reset()
    setPrompt('')
  }

  const isStreaming = state.status === 'streaming' || state.status === 'loading'
  const isDone = state.status === 'done'
  const hasResult = isDone && state.text.length > 0
  const generatedHCL = hasResult ? extractHCL(state.text) : ''

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-2xl flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-zinc-100 font-semibold">Generate HCL with AI</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-xl leading-none">×</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Prompt input */}
          <div>
            <label className="block text-zinc-400 text-xs font-medium mb-1.5">
              Describe what you want to create
            </label>
            <textarea
              ref={promptRef}
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleGenerate() }}
              placeholder="e.g. An S3 bucket with versioning enabled and lifecycle rules to archive objects after 90 days"
              rows={3}
              disabled={isStreaming}
              className="w-full bg-zinc-950 border border-zinc-700 rounded px-3 py-2 text-zinc-100
                         text-sm resize-none placeholder-zinc-500 focus:outline-none
                         focus:border-blue-500 disabled:opacity-50"
            />
          </div>

          {/* Provider selector */}
          <div className="flex items-center gap-3">
            <label className="text-zinc-400 text-xs font-medium">Provider:</label>
            <div className="flex gap-2">
              {PROVIDERS.map(p => (
                <button
                  key={p}
                  onClick={() => setProvider(p)}
                  disabled={isStreaming}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors
                    ${provider === p
                      ? 'bg-blue-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:text-zinc-200'
                    } disabled:opacity-50`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Generated output */}
          {(isStreaming || hasResult) && (
            <div>
              <label className="block text-zinc-400 text-xs font-medium mb-1.5">
                Generated HCL {isStreaming && <span className="text-blue-400 animate-pulse">generating…</span>}
              </label>
              <pre className="bg-zinc-950 border border-zinc-700 rounded p-3 text-xs
                              text-green-300 overflow-auto max-h-60 whitespace-pre-wrap">
                {generatedHCL || state.text}
              </pre>
            </div>
          )}

          {state.status === 'error' && (
            <p className="text-red-400 text-xs">{state.error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-800">
          <button
            onClick={handleReset}
            className="text-zinc-500 hover:text-zinc-300 text-sm"
          >
            Reset
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-sm text-zinc-400 hover:text-zinc-200"
            >
              Cancel
            </button>
            {!hasResult ? (
              <button
                onClick={handleGenerate}
                disabled={isStreaming || !prompt.trim()}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                           text-white text-sm rounded font-medium transition-colors"
              >
                {isStreaming ? 'Generating…' : 'Generate (Ctrl+Enter)'}
              </button>
            ) : (
              <button
                onClick={handleInsert}
                className="px-4 py-1.5 bg-green-600 hover:bg-green-500
                           text-white text-sm rounded font-medium transition-colors"
              >
                Insert into Editor
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
