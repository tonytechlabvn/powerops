// Chat-based refinement panel for AI Studio — conversational loop to refine templates.
// Used by both Creator and Extractor modes after initial generation.

import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import type { ChatMessage, StudioStatus } from '../../types/studio-types'

interface StudioChatPanelProps {
  chatHistory: ChatMessage[]
  status: StudioStatus
  onSendRefinement: (message: string) => void
}

export function StudioChatPanel({ chatHistory, status, onSendRefinement }: StudioChatPanelProps) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || status === 'refining') return
    onSendRefinement(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isRefining = status === 'refining'

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Refine via Chat</h3>

      {/* Message history */}
      {chatHistory.length > 0 && (
        <div className="max-h-48 overflow-y-auto space-y-2 bg-zinc-900/50 rounded p-2">
          {chatHistory.map((msg, i) => (
            <div key={i} className={`text-xs ${msg.role === 'user' ? 'text-blue-300' : 'text-zinc-400'}`}>
              <span className="font-semibold">{msg.role === 'user' ? 'You' : 'AI'}:</span>{' '}
              {msg.content}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Add a security group for SSH access..."
          rows={2}
          disabled={isRefining}
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                     text-zinc-100 text-xs resize-none placeholder-zinc-500
                     focus:outline-none focus:border-blue-500 disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={isRefining || !input.trim()}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                     text-white text-xs rounded font-medium transition-colors self-end"
        >
          {isRefining ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
