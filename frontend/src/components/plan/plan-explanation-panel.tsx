// Collapsible AI plan explanation panel shown below the plan diff.
// Shows deterministic badges immediately, then streams Claude's narrative explanation.

import { useState, useEffect, useRef } from 'react'
import { apiClient } from '../../services/api-client'
import { PlanRiskBadge } from './plan-risk-badge'
import type { PlanAnalysisResponse } from '../../types/api-types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

interface PlanExplanationPanelProps {
  planJson: Record<string, unknown>
}

export function PlanExplanationPanel({ planJson }: PlanExplanationPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [analysis, setAnalysis] = useState<PlanAnalysisResponse | null>(null)
  const [explanation, setExplanation] = useState('')
  const [explainStatus, setExplainStatus] = useState<'idle' | 'loading' | 'streaming' | 'done' | 'error'>('idle')
  const [explainError, setExplainError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Load deterministic analysis immediately when panel opens
  useEffect(() => {
    if (!isOpen || analysis) return
    apiClient
      .post<PlanAnalysisResponse>('/api/plans/analyze', { plan_json: planJson })
      .then(setAnalysis)
      .catch(() => {/* analysis is optional — panel still works without it */})
  }, [isOpen, analysis, planJson])

  const handleExplain = async () => {
    if (explainStatus === 'streaming' || explainStatus === 'loading') return
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setExplanation('')
    setExplainError(null)
    setExplainStatus('loading')

    try {
      const res = await fetch(`${BASE_URL}/api/plans/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        credentials: 'include',
        body: JSON.stringify({ plan_json: planJson }),
        signal: controller.signal,
      })
      if (!res.ok || !res.body) throw new Error(`Request failed: ${res.status}`)

      setExplainStatus('streaming')
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') { setExplainStatus('done'); return }
          setExplanation(prev => prev + data.replace(/\\n/g, '\n'))
        }
      }
      setExplainStatus('done')
    } catch (err) {
      if (controller.signal.aborted) return
      setExplainStatus('error')
      setExplainError(err instanceof Error ? err.message : 'Explanation failed')
    }
  }

  const isExplaining = explainStatus === 'streaming' || explainStatus === 'loading'

  return (
    <div className="border border-zinc-800 rounded-lg bg-zinc-900 mt-4">
      {/* Collapsible header */}
      <button
        onClick={() => setIsOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-zinc-200 font-medium text-sm">AI Plan Analysis</span>
          {analysis && (
            <PlanRiskBadge level={analysis.risk.level} size="sm" />
          )}
          {analysis && (
            <span className={`text-xs font-medium ${
              analysis.cost.direction === 'increase' ? 'text-orange-400' :
              analysis.cost.direction === 'decrease' ? 'text-green-400' : 'text-zinc-400'
            }`}>
              {analysis.cost.estimate}
            </span>
          )}
        </div>
        <span className="text-zinc-500 text-sm">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="border-t border-zinc-800 px-4 py-4 space-y-4">
          {/* Summary stats row */}
          {analysis && (
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Create', value: analysis.summary.creates, color: 'text-green-400' },
                { label: 'Update', value: analysis.summary.updates, color: 'text-yellow-400' },
                { label: 'Destroy', value: analysis.summary.destroys, color: 'text-red-400' },
                { label: 'Replace', value: analysis.summary.replacements, color: 'text-orange-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-zinc-950 rounded p-2 text-center">
                  <div className={`text-lg font-bold ${color}`}>{value}</div>
                  <div className="text-zinc-500 text-xs">{label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Risk flags */}
          {analysis && analysis.risk.flags.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-zinc-400 text-xs font-medium uppercase tracking-wide">Risk Flags</h4>
              {analysis.risk.flags.map((flag, i) => (
                <div key={i} className="flex gap-2 text-xs">
                  <span className={`shrink-0 font-medium ${
                    flag.type === 'data_loss' ? 'text-red-400' :
                    flag.type === 'security' ? 'text-orange-400' : 'text-yellow-400'
                  }`}>
                    {flag.type.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="text-zinc-400">{flag.resource}: {flag.reason}</span>
                </div>
              ))}
            </div>
          )}

          {/* AI narrative explanation */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-zinc-400 text-xs font-medium uppercase tracking-wide">
                AI Explanation
              </h4>
              <button
                onClick={handleExplain}
                disabled={isExplaining}
                className="px-3 py-1 bg-blue-700 hover:bg-blue-600 disabled:opacity-40
                           text-white text-xs rounded font-medium transition-colors"
              >
                {isExplaining ? 'Explaining…' : explainStatus === 'done' ? 'Re-explain' : 'Explain this plan'}
              </button>
            </div>
            {explanation && (
              <div className="bg-zinc-950 rounded p-3 text-zinc-300 text-xs leading-relaxed whitespace-pre-wrap">
                {explanation}
                {isExplaining && <span className="text-blue-400 animate-pulse">▋</span>}
              </div>
            )}
            {explainError && <p className="text-red-400 text-xs mt-1">{explainError}</p>}
          </div>
        </div>
      )}
    </div>
  )
}
