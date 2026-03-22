// TFC Settings Panel — embedded in project detail to manage HCP Terraform Cloud integration.
// Shows connect form when not yet configured; workspace list, sync, variable editor,
// and run history once connected.

import { useState, useEffect, useCallback } from 'react'
import { Cloud, RefreshCw, Play, Check, X, ChevronDown, ChevronUp, Eye, EyeOff } from 'lucide-react'
import { apiClient } from '../../services/api-client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TFCWorkspace {
  id: string
  name: string
  org_name: string
  execution_mode: string
  auto_apply: boolean
  locked: boolean
  terraform_version: string
  created_at: string | null
}

interface TFCRun {
  id: string
  status: string
  message: string
  auto_apply: boolean
  is_destroy: boolean
  workspace_id: string
  created_at: string | null
}

interface TFCVariableEntry {
  key: string
  value: string
  category: 'terraform' | 'env'
  sensitive: boolean
}

interface Props {
  projectId: string
}

// ---------------------------------------------------------------------------
// Status badge helper
// ---------------------------------------------------------------------------

const RUN_STATUS_COLORS: Record<string, string> = {
  pending:             'bg-zinc-500/20 text-zinc-400',
  planning:            'bg-blue-500/20 text-blue-400',
  planned:             'bg-blue-500/20 text-blue-400',
  cost_estimating:     'bg-yellow-500/20 text-yellow-400',
  cost_estimated:      'bg-yellow-500/20 text-yellow-400',
  policy_checking:     'bg-yellow-500/20 text-yellow-400',
  policy_checked:      'bg-yellow-500/20 text-yellow-400',
  planned_and_finished:'bg-green-500/20 text-green-400',
  apply_queued:        'bg-blue-500/20 text-blue-400',
  applying:            'bg-yellow-500/20 text-yellow-400',
  applied:             'bg-green-500/20 text-green-400',
  discarded:           'bg-zinc-500/20 text-zinc-400',
  errored:             'bg-red-500/20 text-red-400',
  canceled:            'bg-zinc-500/20 text-zinc-400',
  force_canceled:      'bg-red-500/20 text-red-400',
}

function RunStatusBadge({ status }: { status: string }) {
  const color = RUN_STATUS_COLORS[status] ?? 'bg-zinc-500/20 text-zinc-400'
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Connect form (shown when TFC not yet configured)
// ---------------------------------------------------------------------------

function ConnectForm({ projectId, onConnected }: { projectId: string; onConnected: () => void }) {
  const [orgName, setOrgName] = useState('')
  const [apiToken, setApiToken] = useState('')
  const [showToken, setShowToken] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleConnect() {
    if (!orgName.trim() || !apiToken.trim()) {
      setError('Organisation name and API token are required.')
      return
    }
    setSaving(true)
    setError('')
    try {
      await apiClient.post(`/api/projects/${projectId}/tfc/setup`, {
        org_name: orgName.trim(),
        api_token: apiToken.trim(),
      })
      onConnected()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save TFC credentials.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 max-w-md">
      <div className="flex items-center gap-2 mb-4">
        <Cloud size={18} className="text-blue-400" />
        <h3 className="text-zinc-100 font-medium">Connect to HCP Terraform Cloud</h3>
      </div>

      <p className="text-zinc-500 text-sm mb-5">
        Enter your TFC organisation and a user or team API token to link this project.
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Organisation name</label>
          <input
            type="text"
            value={orgName}
            onChange={e => setOrgName(e.target.value)}
            placeholder="my-org"
            className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm placeholder-zinc-600 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs text-zinc-500 mb-1">API token</label>
          <div className="relative">
            <input
              type={showToken ? 'text' : 'password'}
              value={apiToken}
              onChange={e => setApiToken(e.target.value)}
              placeholder="••••••••••••••••"
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 pr-9 text-sm placeholder-zinc-600 focus:outline-none focus:border-blue-500"
            />
            <button
              type="button"
              onClick={() => setShowToken(s => !s)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
            >
              {showToken ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
        </div>

        {error && <p className="text-red-400 text-xs">{error}</p>}

        <button
          onClick={handleConnect}
          disabled={saving}
          className="w-full bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
        >
          {saving ? 'Connecting…' : 'Connect'}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Variable editor row
// ---------------------------------------------------------------------------

function VariableRow({
  variable,
  onRemove,
  onChange,
}: {
  variable: TFCVariableEntry
  onRemove: () => void
  onChange: (updated: TFCVariableEntry) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={variable.key}
        onChange={e => onChange({ ...variable, key: e.target.value })}
        placeholder="KEY"
        className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-2 py-1.5 text-xs placeholder-zinc-600 focus:outline-none focus:border-blue-500"
      />
      <input
        type={variable.sensitive ? 'password' : 'text'}
        value={variable.value}
        onChange={e => onChange({ ...variable, value: e.target.value })}
        placeholder="value"
        className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-2 py-1.5 text-xs placeholder-zinc-600 focus:outline-none focus:border-blue-500"
      />
      <select
        value={variable.category}
        onChange={e => onChange({ ...variable, category: e.target.value as 'terraform' | 'env' })}
        className="bg-zinc-800 border border-zinc-700 text-zinc-400 rounded px-2 py-1.5 text-xs focus:outline-none focus:border-blue-500"
      >
        <option value="terraform">terraform</option>
        <option value="env">env</option>
      </select>
      <label className="flex items-center gap-1 text-xs text-zinc-500 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={variable.sensitive}
          onChange={e => onChange({ ...variable, sensitive: e.target.checked })}
          className="accent-blue-500"
        />
        sensitive
      </label>
      <button
        onClick={onRemove}
        className="text-zinc-600 hover:text-red-400 transition-colors"
        title="Remove variable"
      >
        <X size={14} />
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Connected view
// ---------------------------------------------------------------------------

function ConnectedView({ projectId }: { projectId: string }) {
  const [workspaces, setWorkspaces] = useState<TFCWorkspace[]>([])
  const [runs, setRuns] = useState<TFCRun[]>([])
  const [selectedWsId, setSelectedWsId] = useState<string | null>(null)
  const [variables, setVariables] = useState<TFCVariableEntry[]>([
    { key: '', value: '', category: 'terraform', sensitive: false },
  ])
  const [loadingWs, setLoadingWs] = useState(true)
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [pushingVars, setPushingVars] = useState(false)
  const [triggeringRun, setTriggeringRun] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [showVars, setShowVars] = useState(false)

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg)
    setTimeout(() => setSuccessMsg(''), 3000)
  }

  const fetchWorkspaces = useCallback(async () => {
    setLoadingWs(true)
    setError('')
    try {
      const data = await apiClient.get<TFCWorkspace[]>(`/api/projects/${projectId}/tfc/workspaces`)
      setWorkspaces(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load workspaces.')
    } finally {
      setLoadingWs(false)
    }
  }, [projectId])

  const fetchRuns = useCallback(async (wsId: string) => {
    setLoadingRuns(true)
    try {
      const data = await apiClient.get<TFCRun[]>(
        `/api/projects/${projectId}/tfc/runs`,
        { workspace_id: wsId },
      )
      setRuns(data)
    } catch {
      setRuns([])
    } finally {
      setLoadingRuns(false)
    }
  }, [projectId])

  useEffect(() => { fetchWorkspaces() }, [fetchWorkspaces])

  useEffect(() => {
    if (selectedWsId) fetchRuns(selectedWsId)
  }, [selectedWsId, fetchRuns])

  async function handleSync() {
    setSyncing(true)
    setError('')
    try {
      const result = await apiClient.post<{ created: string[]; updated: string[]; skipped: string[] }>(
        `/api/projects/${projectId}/tfc/sync`,
      )
      showSuccess(
        `Sync complete — created: ${result.created.length}, updated: ${result.updated.length}, skipped: ${result.skipped.length}`,
      )
      await fetchWorkspaces()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Sync failed.')
    } finally {
      setSyncing(false)
    }
  }

  async function handlePushVars() {
    if (!selectedWsId) {
      setError('Select a workspace first.')
      return
    }
    const validVars = variables.filter(v => v.key.trim())
    if (validVars.length === 0) {
      setError('Add at least one variable with a non-empty key.')
      return
    }
    setPushingVars(true)
    setError('')
    try {
      const result = await apiClient.post<{ created: string[]; updated: string[] }>(
        `/api/projects/${projectId}/tfc/variables`,
        { workspace_id: selectedWsId, variables: validVars },
      )
      showSuccess(`Variables pushed — created: ${result.created.length}, updated: ${result.updated.length}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to push variables.')
    } finally {
      setPushingVars(false)
    }
  }

  async function handleTriggerRun() {
    if (!selectedWsId) {
      setError('Select a workspace first.')
      return
    }
    setTriggeringRun(true)
    setError('')
    try {
      const run = await apiClient.post<TFCRun>(`/api/projects/${projectId}/tfc/runs`, {
        workspace_id: selectedWsId,
        message: 'Triggered from PowerOps',
        auto_apply: false,
      })
      showSuccess(`Run queued — ID: ${run.id}`)
      await fetchRuns(selectedWsId)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to trigger run.')
    } finally {
      setTriggeringRun(false)
    }
  }

  async function handleRunAction(runId: string, action: 'apply' | 'discard') {
    try {
      await apiClient.post(`/api/projects/${projectId}/tfc/runs/${runId}/${action}`, {})
      showSuccess(`Run ${action}ed`)
      if (selectedWsId) await fetchRuns(selectedWsId)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${action} run.`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 text-green-400 text-sm">
          <Check size={14} />
          <span>Connected to TFC</span>
        </div>

        <button
          onClick={fetchWorkspaces}
          className="flex items-center gap-1 text-zinc-500 hover:text-zinc-300 text-xs transition-colors"
          title="Refresh workspaces"
        >
          <RefreshCw size={13} />
          Refresh
        </button>

        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Syncing…' : 'Sync Modules'}
        </button>

        {selectedWsId && (
          <button
            onClick={handleTriggerRun}
            disabled={triggeringRun}
            className="flex items-center gap-2 bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/30 rounded px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
          >
            <Play size={13} />
            {triggeringRun ? 'Queueing…' : 'Trigger Run'}
          </button>
        )}
      </div>

      {/* Feedback */}
      {error && (
        <p className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {error}
        </p>
      )}
      {successMsg && (
        <p className="text-green-400 text-xs bg-green-500/10 border border-green-500/20 rounded px-3 py-2">
          {successMsg}
        </p>
      )}

      {/* Workspace list */}
      <div>
        <h4 className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Workspaces</h4>
        {loadingWs ? (
          <p className="text-zinc-500 text-sm">Loading…</p>
        ) : workspaces.length === 0 ? (
          <p className="text-zinc-500 text-sm">
            No workspaces found. Click "Sync Modules" to create them.
          </p>
        ) : (
          <div className="space-y-2">
            {workspaces.map(ws => (
              <button
                key={ws.id}
                onClick={() => setSelectedWsId(prev => prev === ws.id ? null : ws.id)}
                className={`w-full text-left bg-zinc-900 border rounded-lg p-3 transition-colors ${
                  selectedWsId === ws.id
                    ? 'border-blue-500/50 bg-blue-500/5'
                    : 'border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cloud size={14} className="text-zinc-500" />
                    <span className="text-zinc-100 text-sm font-medium">{ws.name}</span>
                    <span className="text-xs text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">
                      {ws.execution_mode}
                    </span>
                    {ws.locked && (
                      <span className="text-xs text-yellow-400 bg-yellow-500/10 px-1.5 py-0.5 rounded">
                        locked
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-zinc-600">{ws.id}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Variable editor — shown when a workspace is selected */}
      {selectedWsId && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <button
            onClick={() => setShowVars(s => !s)}
            className="flex items-center justify-between w-full mb-3"
          >
            <h4 className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
              Push Variables
            </h4>
            {showVars ? <ChevronUp size={14} className="text-zinc-500" /> : <ChevronDown size={14} className="text-zinc-500" />}
          </button>

          {showVars && (
            <div className="space-y-2">
              {variables.map((v, idx) => (
                <VariableRow
                  key={idx}
                  variable={v}
                  onChange={updated => {
                    setVariables(prev => prev.map((x, i) => i === idx ? updated : x))
                  }}
                  onRemove={() => setVariables(prev => prev.filter((_, i) => i !== idx))}
                />
              ))}

              <div className="flex items-center gap-3 pt-1">
                <button
                  onClick={() =>
                    setVariables(prev => [
                      ...prev,
                      { key: '', value: '', category: 'terraform', sensitive: false },
                    ])
                  }
                  className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                  + Add variable
                </button>

                <button
                  onClick={handlePushVars}
                  disabled={pushingVars}
                  className="ml-auto flex items-center gap-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded px-3 py-1.5 text-xs font-medium transition-colors"
                >
                  {pushingVars ? 'Pushing…' : 'Push Variables'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Run history — shown when a workspace is selected */}
      {selectedWsId && (
        <div>
          <h4 className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">
            Run History
          </h4>
          {loadingRuns ? (
            <p className="text-zinc-500 text-sm">Loading runs…</p>
          ) : runs.length === 0 ? (
            <p className="text-zinc-500 text-sm">No runs yet for this workspace.</p>
          ) : (
            <div className="space-y-2">
              {runs.map(run => (
                <div
                  key={run.id}
                  className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <RunStatusBadge status={run.status} />
                    <span className="text-zinc-400 text-xs truncate">
                      {run.message || run.id}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {run.created_at && (
                      <span className="text-zinc-600 text-xs">
                        {new Date(run.created_at).toLocaleString()}
                      </span>
                    )}
                    {run.status === 'planned' && (
                      <>
                        <button
                          onClick={() => handleRunAction(run.id, 'apply')}
                          className="text-xs text-green-400 hover:text-green-300 bg-green-500/10 border border-green-500/20 rounded px-2 py-1 transition-colors"
                        >
                          Apply
                        </button>
                        <button
                          onClick={() => handleRunAction(run.id, 'discard')}
                          className="text-xs text-red-400 hover:text-red-300 bg-red-500/10 border border-red-500/20 rounded px-2 py-1 transition-colors"
                        >
                          Discard
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export function TFCSettingsPanel({ projectId }: Props) {
  // Attempt to load workspaces to determine if already connected
  const [connected, setConnected] = useState<boolean | null>(null)

  useEffect(() => {
    apiClient
      .get(`/api/projects/${projectId}/tfc/workspaces`)
      .then(() => setConnected(true))
      .catch((err: unknown) => {
        // 400 = not configured; anything else = server/auth error but treat as disconnected
        setConnected(false)
        // Suppress noise — expected when TFC not yet set up
        void err
      })
  }, [projectId])

  if (connected === null) {
    return <div className="text-zinc-500 text-sm p-4">Checking TFC connection…</div>
  }

  return (
    <div>
      {connected ? (
        <ConnectedView projectId={projectId} />
      ) : (
        <ConnectForm projectId={projectId} onConnected={() => setConnected(true)} />
      )}
    </div>
  )
}
