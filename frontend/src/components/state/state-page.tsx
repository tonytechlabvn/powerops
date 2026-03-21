// State management page: workspace selector, version history, lock status, outputs

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, Lock, Unlock, RotateCcw, RefreshCw, Loader2 } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import { formatDate } from '../../lib/utils'
import type { StateVersion, StateLockInfo } from '../../types/api-types'

interface Workspace { id: string; name: string; provider: string; environment: string }
interface VersionsResponse { workspace: string; versions: StateVersion[] }
interface OutputsResponse { workspace: string; outputs: Record<string, unknown> }

const q = {
  workspaces: () => ({ queryKey: ['workspaces'], queryFn: () => apiClient.get<Workspace[]>('/api/workspaces') }),
  versions: (ws: string) => ({ queryKey: ['state', ws, 'versions'], queryFn: () => apiClient.get<VersionsResponse>(`/api/state/${ws}/versions`), enabled: !!ws }),
  lockinfo: (ws: string) => ({ queryKey: ['state', ws, 'lock'], queryFn: async () => { try { return await apiClient.post<StateLockInfo>(`/api/state/${ws}/lock`) } catch { return null } }, enabled: !!ws }),
  outputs: (ws: string) => ({ queryKey: ['state', ws, 'outputs'], queryFn: () => apiClient.get<OutputsResponse>(`/api/state/${ws}/outputs`), enabled: !!ws }),
}

// --- Lock status panel ---
function LockPanel({ ws }: { ws: string }) {
  const qc = useQueryClient()
  const { data: info, isLoading } = useQuery(q.lockinfo(ws))
  const unlock = useMutation({
    mutationFn: () => apiClient.del(`/api/state/${ws}/lock`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['state', ws, 'lock'] }),
  })

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-3">
      <p className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><Lock size={15} className="text-zinc-400" /> Lock Status</p>
      {isLoading ? <Loader2 size={14} className="animate-spin text-zinc-500" /> : info ? (
        <div className="space-y-2">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
            {([['Who', info.Who], ['Operation', info.Operation], ['Created', formatDate(info.Created)]] as [string, string][]).map(([k, v]) => (
              <><dt key={k} className="text-zinc-500">{k}</dt><dd key={k+'v'} className="text-zinc-200 font-mono">{v}</dd></>
            ))}
          </dl>
          <button onClick={() => unlock.mutate()} disabled={unlock.isPending}
            className="flex items-center gap-1.5 text-xs bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-400 px-3 py-1.5 rounded transition-colors">
            {unlock.isPending ? <Loader2 size={12} className="animate-spin" /> : <Unlock size={12} />} Force Unlock
          </button>
        </div>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-xs text-green-400 bg-green-500/10 border border-green-500/30 rounded-full px-3 py-1">
          <Unlock size={12} /> Unlocked
        </span>
      )}
    </div>
  )
}

// --- Outputs panel ---
function OutputsPanel({ ws }: { ws: string }) {
  const { data, isLoading } = useQuery(q.outputs(ws))
  const entries = Object.entries(data?.outputs ?? {})
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-3">
      <p className="text-sm font-semibold text-zinc-100">Outputs</p>
      {isLoading ? <Loader2 size={14} className="animate-spin text-zinc-500" />
        : entries.length === 0 ? <p className="text-sm text-zinc-500">No outputs</p>
        : <div className="space-y-1">{entries.map(([k, v]) => (
            <div key={k} className="flex gap-3 text-xs font-mono">
              <span className="text-blue-400 shrink-0">{k}</span>
              <span className="text-zinc-300 break-all">{JSON.stringify(v)}</span>
            </div>
          ))}</div>}
    </div>
  )
}

// --- Version history table ---
function VersionsTable({ ws }: { ws: string }) {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery(q.versions(ws))
  const [confirmSerial, setConfirm] = useState<number | null>(null)
  const rollback = useMutation({
    mutationFn: (serial: number) => apiClient.post(`/api/state/${ws}/rollback/${serial}`),
    onSuccess: () => { setConfirm(null); void qc.invalidateQueries({ queryKey: ['state', ws, 'versions'] }) },
  })
  const versions = data?.versions ?? []

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
        <p className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><Database size={15} className="text-zinc-400" /> State Versions</p>
        <button onClick={() => void qc.invalidateQueries({ queryKey: ['state', ws, 'versions'] })} className="text-zinc-500 hover:text-zinc-300 transition-colors">
          <RefreshCw size={14} />
        </button>
      </div>

      {isLoading ? <div className="flex items-center gap-2 px-5 py-6 text-sm text-zinc-500"><Loader2 size={14} className="animate-spin" /> Loading…</div>
        : error ? <p className="px-5 py-6 text-sm text-red-400">Failed to load versions.</p>
        : versions.length === 0 ? <p className="px-5 py-6 text-sm text-zinc-500">No state versions yet</p>
        : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wide">
              {['Serial', 'Checksum', 'Created At', 'Created By', ''].map(h => <th key={h} className="px-5 py-3 text-left font-medium">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {versions.map(v => (
              <tr key={v.id} className="border-b border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
                <td className="px-5 py-3 text-zinc-100 font-mono">#{v.serial}</td>
                <td className="px-5 py-3 text-zinc-400 font-mono">{v.checksum.slice(0, 12)}…</td>
                <td className="px-5 py-3 text-zinc-300">{formatDate(v.created_at)}</td>
                <td className="px-5 py-3 text-zinc-400">{v.created_by}</td>
                <td className="px-5 py-3 text-right">
                  {confirmSerial === v.serial ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="text-xs text-zinc-400">Confirm?</span>
                      <button onClick={() => rollback.mutate(v.serial)} disabled={rollback.isPending}
                        className="text-xs bg-red-600 hover:bg-red-500 text-white px-2 py-1 rounded">
                        {rollback.isPending ? <Loader2 size={10} className="animate-spin inline" /> : 'Yes'}
                      </button>
                      <button onClick={() => setConfirm(null)} className="text-xs text-zinc-500 hover:text-zinc-300">Cancel</button>
                    </span>
                  ) : (
                    <button onClick={() => setConfirm(v.serial)}
                      className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors ml-auto">
                      <RotateCcw size={11} /> Rollback
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// --- Main export ---
export function StatePage() {
  const { data: workspaces, isLoading: wsLoading } = useQuery(q.workspaces())
  const [selected, setSelected] = useState<string | null>(null)
  const ws = selected ?? workspaces?.[0]?.name ?? null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">State</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage Terraform state versions and locks</p>
        </div>
        <div className="flex items-center gap-2">
          {wsLoading && <Loader2 size={14} className="animate-spin text-zinc-500" />}
          <select value={ws ?? ''} onChange={e => setSelected(e.target.value || null)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-3 py-2 focus:outline-none focus:border-blue-500">
            {!workspaces?.length && <option value="">No workspaces</option>}
            {workspaces?.map(w => <option key={w.id} value={w.name}>{w.name}</option>)}
          </select>
        </div>
      </div>

      {ws ? (
        <>
          <VersionsTable ws={ws} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <LockPanel ws={ws} />
            <OutputsPanel ws={ws} />
          </div>
        </>
      ) : (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-10 text-center text-sm text-zinc-500">
          Select a workspace to view state
        </div>
      )}
    </div>
  )
}
