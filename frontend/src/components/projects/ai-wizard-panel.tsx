// AI Project Wizard panel — conversational chat UI that generates a project.yaml

import { useEffect, useRef, useState } from 'react'
import { Send, Sparkles, Code2 } from 'lucide-react'
import { apiClient } from '../../services/api-client'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Props {
  onCreated: () => void
}

export function AiWizardPanel({ onCreated }: Props) {
  const [messages, setMessages]         = useState<Message[]>([])
  const [input, setInput]               = useState('')
  const [sending, setSending]           = useState(false)
  const [projectYaml, setProjectYaml]   = useState<string | null>(null)
  const [projectName, setProjectName]   = useState('')
  const [confirming, setConfirming]     = useState(false)
  const [confirmError, setConfirmError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Seed the first assistant greeting on mount
  useEffect(() => {
    setMessages([{
      role: 'assistant',
      content: "Hi! I'm the PowerOps Project Wizard. Tell me what kind of infrastructure you want to build and I'll design a project configuration for you.\n\nFor example: *\"I need a web app on AWS with a load balancer and a managed database\"* or *\"Set up a Proxmox database cluster with replication\"*.",
    }])
  }, [])

  async function sendMessage() {
    const text = input.trim()
    if (!text || sending) return

    const newHistory: Message[] = [...messages, { role: 'user', content: text }]
    setMessages(newHistory)
    setInput('')
    setSending(true)
    setProjectYaml(null)
    setConfirmError(null)

    try {
      const res = await apiClient.post<{ response: string; project_yaml: string | null }>(
        '/api/project-wizard/message',
        {
          message: text,
          history: messages.map(m => ({ role: m.role, content: m.content })),
        }
      )
      setMessages([...newHistory, { role: 'assistant', content: res.response }])
      if (res.project_yaml) {
        setProjectYaml(res.project_yaml)
      }
    } catch (err) {
      setMessages([
        ...newHistory,
        {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${err instanceof Error ? err.message : 'Unknown error'}. Please try again.`,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  async function handleConfirm() {
    if (!projectYaml) return
    setConfirmError(null)
    setConfirming(true)
    try {
      await apiClient.post('/api/project-wizard/confirm', {
        project_yaml: projectYaml,
        project_name: projectName.trim(),
      })
      onCreated()
    } catch (err) {
      setConfirmError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="flex flex-col h-full min-h-0" style={{ maxHeight: '520px' }}>
      {/* Message history */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 mb-3">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="shrink-0 w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center mt-0.5">
                <Sparkles size={12} className="text-blue-400" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-500/20 text-blue-100'
                  : 'bg-zinc-800 text-zinc-200'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex gap-2.5 justify-start">
            <div className="shrink-0 w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center mt-0.5">
              <Sparkles size={12} className="text-blue-400 animate-pulse" />
            </div>
            <div className="bg-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-400">
              Thinking...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Generated YAML preview + confirm */}
      {projectYaml && (
        <div className="border border-blue-500/30 bg-blue-500/5 rounded-lg p-3 mb-3 space-y-2.5">
          <div className="flex items-center gap-1.5 text-xs text-blue-400 font-medium">
            <Code2 size={13} />
            Project YAML generated
          </div>
          <pre className="text-xs font-mono text-zinc-300 bg-zinc-900 rounded p-2 overflow-x-auto max-h-40 overflow-y-auto">
            {projectYaml}
          </pre>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={projectName}
              onChange={e => setProjectName(e.target.value)}
              placeholder="Project name (optional)"
              className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-2.5 py-1.5 text-xs placeholder-zinc-600 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleConfirm}
              disabled={confirming}
              className="px-3 py-1.5 text-xs bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 disabled:cursor-not-allowed text-white font-medium rounded transition-colors shrink-0"
            >
              {confirming ? 'Creating...' : 'Create Project'}
            </button>
          </div>
          {confirmError && (
            <p className="text-red-400 text-xs">{confirmError}</p>
          )}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 items-end shrink-0">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
          rows={2}
          placeholder="Describe your infrastructure... (Enter to send, Shift+Enter for newline)"
          className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm placeholder-zinc-600 focus:outline-none focus:border-blue-500 resize-none disabled:opacity-50"
        />
        <button
          onClick={sendMessage}
          disabled={sending || !input.trim()}
          className="p-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white rounded transition-colors shrink-0"
          title="Send message"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
