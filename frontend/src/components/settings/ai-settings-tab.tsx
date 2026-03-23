// AI model provider configuration tab for Settings page
// Models fetched dynamically from each provider's API via GET /api/config/ai/models

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import { cn } from '../../lib/utils'
import type { AIConfigResponse, AIConfigRequest, AIProviderStatus, AIModelInfo } from '../../types/api-types'

// Provider display metadata
const PROVIDER_META: Record<string, { label: string; description: string; needsKey: boolean }> = {
  anthropic: { label: 'Anthropic (Claude)', description: 'Claude models via Anthropic API', needsKey: true },
  openai: { label: 'OpenAI', description: 'GPT models via OpenAI API', needsKey: true },
  gemini: { label: 'Google Gemini', description: 'Gemini models via Google AI API', needsKey: true },
  ollama: { label: 'Ollama (Local)', description: 'Local LLM via Ollama server', needsKey: false },
}

export function AISettingsTab() {
  const qc = useQueryClient()

  // Fetch current AI config
  const { data: config, isLoading: loadingConfig } = useQuery({
    queryKey: ['ai-config'],
    queryFn: () => apiClient.get<AIConfigResponse>('/api/config/ai'),
  })

  // Fetch provider status list
  const { data: providers } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => apiClient.get<AIProviderStatus[]>('/api/config/ai/providers'),
  })

  // Form state
  const [provider, setProvider] = useState('anthropic')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [customModel, setCustomModel] = useState('')
  const [useCustomModel, setUseCustomModel] = useState(false)
  const [maxTokens, setMaxTokens] = useState(4096)
  const [baseUrl, setBaseUrl] = useState('http://localhost:11434')
  const [saved, setSaved] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Fetch models dynamically from provider API
  const { data: fetchedModels, isLoading: loadingModels, refetch: refetchModels } = useQuery({
    queryKey: ['ai-models', provider],
    queryFn: () => apiClient.get<AIModelInfo[]>(`/api/config/ai/models?provider=${provider}`),
    enabled: !!provider,
    staleTime: 5 * 60 * 1000, // cache for 5 minutes
    retry: 1,
  })

  // Sync form with fetched config
  useEffect(() => {
    if (config) {
      setProvider(config.provider)
      setModel(config.model)
      setMaxTokens(config.max_tokens)
      if (config.base_url) setBaseUrl(config.base_url)
    }
  }, [config])

  // When models load, check if current model is in the list
  useEffect(() => {
    if (fetchedModels && fetchedModels.length > 0 && model) {
      const inList = fetchedModels.some(m => m.id === model)
      if (!inList) {
        setCustomModel(model)
        setUseCustomModel(true)
      } else {
        setUseCustomModel(false)
      }
    }
  }, [fetchedModels, model])

  const saveMutation = useMutation({
    mutationFn: (payload: AIConfigRequest) =>
      apiClient.post<{ message: string }>('/api/config/ai', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ai-config'] })
      qc.invalidateQueries({ queryKey: ['ai-providers'] })
      setSaved(true)
      setApiKey('')
      setTimeout(() => setSaved(false), 3000)
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : 'Save failed')
    },
  })

  function handleSave() {
    setFormError(null)
    setSaved(false)

    const meta = PROVIDER_META[provider]
    if (meta?.needsKey && !apiKey && !config?.api_key_set) {
      setFormError('API key is required for this provider.')
      return
    }

    const selectedModel = useCustomModel ? customModel : model
    const payload: AIConfigRequest = {
      provider,
      model: selectedModel || undefined,
      max_tokens: maxTokens,
    }
    if (apiKey) payload.api_key = apiKey
    if (provider === 'ollama') payload.base_url = baseUrl

    saveMutation.mutate(payload)
  }

  if (loadingConfig) return <p className="text-zinc-500 text-sm py-4">Loading...</p>

  const meta = PROVIDER_META[provider] || { label: provider, description: '', needsKey: true }
  const models = fetchedModels ?? []
  const hasModels = models.length > 0

  return (
    <div className="space-y-6">
      {/* Active provider config */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-zinc-100">AI Provider</h2>
          <p className="text-sm text-zinc-500 mt-1">Configure which LLM provider powers AI features</p>
        </div>

        {/* Provider selector */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-zinc-300">Provider</label>
          <select
            value={provider}
            onChange={e => { setProvider(e.target.value); setSaved(false); setFormError(null); setUseCustomModel(false) }}
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
          >
            {Object.entries(PROVIDER_META).map(([key, p]) => (
              <option key={key} value={key}>{p.label}</option>
            ))}
          </select>
          <p className="text-xs text-zinc-500">{meta.description}</p>
        </div>

        {/* API Key (not shown for Ollama) */}
        {meta.needsKey && (
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-zinc-300">API Key</label>
            <div className="relative">
              <input
                type="password"
                value={apiKey}
                onChange={e => { setApiKey(e.target.value); setSaved(false) }}
                placeholder={config?.api_key_set && config.provider === provider ? '••••••••  (already set)' : 'Enter API key'}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-blue-500"
              />
              {config?.api_key_set && config.provider === provider && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2">
                  <CheckCircle size={14} className="text-green-400" />
                </span>
              )}
            </div>
          </div>
        )}

        {/* Ollama Base URL */}
        {provider === 'ollama' && (
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-zinc-300">Ollama Server URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={e => { setBaseUrl(e.target.value); setSaved(false) }}
              placeholder="http://localhost:11434"
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        )}

        {/* Model selector — dynamic from API */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-zinc-300">Model</label>
            <div className="flex items-center gap-2">
              {loadingModels && <Loader2 size={12} className="animate-spin text-zinc-500" />}
              <button
                onClick={() => refetchModels()}
                disabled={loadingModels}
                className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-50"
                title="Refresh model list from provider API"
              >
                <RefreshCw size={12} />
                Refresh
              </button>
              <button
                onClick={() => setUseCustomModel(!useCustomModel)}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                {useCustomModel ? 'Select from list' : 'Enter manually'}
              </button>
            </div>
          </div>

          {useCustomModel ? (
            <input
              type="text"
              value={customModel}
              onChange={e => { setCustomModel(e.target.value); setSaved(false) }}
              placeholder="Enter model ID (e.g. gpt-4o, claude-sonnet-4-20250514)"
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-blue-500"
            />
          ) : hasModels ? (
            <select
              value={model}
              onChange={e => { setModel(e.target.value); setSaved(false) }}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
            >
              {models.map(m => (
                <option key={m.id} value={m.id}>
                  {m.name !== m.id ? `${m.name} (${m.id})` : m.id}
                </option>
              ))}
            </select>
          ) : (
            <div className="space-y-2">
              <input
                type="text"
                value={model}
                onChange={e => { setModel(e.target.value); setSaved(false) }}
                placeholder="Enter model name"
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-blue-500"
              />
              {!loadingModels && (
                <p className="text-xs text-zinc-500">
                  {meta.needsKey && !config?.api_key_set
                    ? 'Save API key first to load available models'
                    : 'No models found — enter model ID manually or click Refresh'}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Max Tokens */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-zinc-300">Max Tokens</label>
          <input
            type="number"
            value={maxTokens}
            onChange={e => { setMaxTokens(Number(e.target.value) || 4096); setSaved(false) }}
            min={256}
            max={32768}
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Error / Success */}
        {formError && (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle size={14} />
            {formError}
          </div>
        )}

        {saved && (
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <CheckCircle size={14} />
            Configuration saved successfully.
          </div>
        )}

        {/* Save button */}
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
        >
          {saveMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          Save Configuration
        </button>
      </div>

      {/* Provider status overview */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-zinc-100 font-medium text-sm">All Providers</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-500">
              <th className="text-left px-4 py-2 font-medium">Provider</th>
              <th className="text-left px-4 py-2 font-medium">Default Model</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {(providers ?? []).map(p => (
              <tr key={p.name} className="border-b border-zinc-800/50 last:border-0">
                <td className="px-4 py-2 text-zinc-100">
                  {PROVIDER_META[p.name]?.label || p.name}
                  {config?.provider === p.name && (
                    <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30">active</span>
                  )}
                </td>
                <td className="px-4 py-2 text-zinc-400 font-mono text-xs">{p.default_model}</td>
                <td className="px-4 py-2">
                  <span className={cn('text-xs px-2 py-0.5 rounded-full border',
                    p.configured
                      ? 'bg-green-500/10 text-green-400 border-green-500/30'
                      : 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30'
                  )}>
                    {p.configured ? 'configured' : 'not set'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
