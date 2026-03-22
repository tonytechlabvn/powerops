// AI chat sidebar for the HCL editor — conversational assistant with workspace context.
// Streams responses token-by-token and renders markdown-style code blocks.

import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import { useAIEditor } from '../../hooks/use-ai-editor'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface AIChatSidebarProps {
  workspaceId: string
  currentFile?: string
  currentContent?: string
  onClose: () => void
}

export function AIChatSidebar({ workspaceId, currentFile, currentContent, onClose }: AIChatSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const { state, chat, reset } = useAIEditor(workspaceId)
  const bottomRef = useRef<HTMLDivElement>(null)
  const streamingRef = useRef(false)

  // Scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, state.text])

  // When stream completes, commit streamed text to messages array
  useEffect(() => {
    if (state.status === 'done' && streamingRef.current && state.text) {
      setMessages(prev => [...prev, { role: 'assistant', content: state.text }])
      streamingRef.current = false
      reset()
    }
  }, [state.status, state.text, reset])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || state.status === 'streaming' || state.status === 'loading') return

    const userMessage: Message = { role: 'user', content: trimmed }
    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setInput('')
    streamingRef.current = true

    const apiMessages = updatedMessages.map(m => ({ role: m.role, content: m.content }))
    chat(apiMessages, currentFile, currentContent)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isStreaming = state.status === 'streaming' || state.status === 'loading'

  return (
    <div className="flex flex-col h-full bg-zinc-900 border-l border-zinc-800 w-80">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <span className="text-blue-400 text-sm font-semibold">AI Assistant</span>
          {currentFile && (
            <span className="text-zinc-500 text-xs truncate max-w-[120px]">{currentFile}</span>
          )}
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-lg leading-none">
          ×
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-zinc-500 text-xs text-center mt-8">
            Ask anything about your Terraform configuration.
            <br />Tip: Select code in the editor, then ask to explain or fix it.
          </p>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {/* Live streaming message */}
        {isStreaming && state.text && (
          <MessageBubble message={{ role: 'assistant', content: state.text + '▋' }} />
        )}
        {isStreaming && !state.text && (
          <div className="flex gap-1 px-3 py-2">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
        )}
        {state.status === 'error' && (
          <p className="text-red-400 text-xs px-3">{state.error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-zinc-800 p-3">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your HCL... (Enter to send)"
            disabled={isStreaming}
            rows={2}
            className="flex-1 bg-zinc-950 border border-zinc-700 rounded px-3 py-2 text-zinc-100
                       text-xs resize-none placeholder-zinc-500 focus:outline-none
                       focus:border-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                       text-white text-xs rounded font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[90%] rounded px-3 py-2 text-xs whitespace-pre-wrap break-words
          ${isUser
            ? 'bg-blue-600 text-white'
            : 'bg-zinc-800 text-zinc-200 border border-zinc-700'
          }`}
      >
        {message.content}
      </div>
    </div>
  )
}
