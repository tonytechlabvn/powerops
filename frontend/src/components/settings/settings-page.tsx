// Tabbed settings page: Organization, Teams, API Tokens

import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, Shield, Key, Plus, Trash2, Copy, Check } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import { cn, formatDate } from '../../lib/utils'
import type { AuthUser, TeamInfo, OrgInfo, APITokenInfo, APITokenCreated } from '../../types/api-types'

// --- Tab definitions ---
type Tab = 'org' | 'teams' | 'tokens'
const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'org',    label: 'Organization', icon: <Users size={15} /> },
  { id: 'teams',  label: 'Teams',        icon: <Shield size={15} /> },
  { id: 'tokens', label: 'API Tokens',   icon: <Key size={15} /> },
]

// --- Sub-components ---

function OrgTab() {
  const { data: org, isLoading: loadingOrg, error: orgError } = useQuery({
    queryKey: ['org'],
    queryFn: () => apiClient.get<OrgInfo>('/api/org'),
  })
  const { data: users, isLoading: loadingUsers } = useQuery({
    queryKey: ['users'],
    queryFn: () => apiClient.get<AuthUser[]>('/api/users'),
  })

  if (loadingOrg) return <p className="text-zinc-500 text-sm py-4">Loading…</p>
  if (orgError) return <p className="text-red-400 text-sm py-4">Failed to load organization.</p>

  return (
    <div className="space-y-6">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-zinc-500 text-sm w-28">Name</span>
          <span className="text-zinc-100 font-medium">{org?.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-zinc-500 text-sm w-28">Created</span>
          <span className="text-zinc-300 text-sm">{formatDate(org?.created_at)}</span>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-zinc-100 font-medium text-sm">Members</h3>
        </div>
        {loadingUsers ? (
          <p className="text-zinc-500 text-sm p-4">Loading users…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-4 py-2 font-medium">Email</th>
                <th className="text-left px-4 py-2 font-medium">Name</th>
                <th className="text-left px-4 py-2 font-medium">Status</th>
                <th className="text-left px-4 py-2 font-medium">Teams</th>
              </tr>
            </thead>
            <tbody>
              {(users ?? []).map(u => (
                <tr key={u.id} className="border-b border-zinc-800/50 last:border-0">
                  <td className="px-4 py-2 text-zinc-100">{u.email}</td>
                  <td className="px-4 py-2 text-zinc-300">{u.name || '—'}</td>
                  <td className="px-4 py-2">
                    <span className={cn('text-xs px-2 py-0.5 rounded-full border',
                      u.is_active
                        ? 'bg-green-500/10 text-green-400 border-green-500/30'
                        : 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30'
                    )}>
                      {u.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-zinc-400">{u.teams.length ? u.teams.join(', ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function TeamsTab() {
  const qc = useQueryClient()
  const [teamName, setTeamName] = useState('')

  const { data: teams, isLoading, error } = useQuery({
    queryKey: ['teams'],
    queryFn: () => apiClient.get<TeamInfo[]>('/api/teams'),
  })
  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => apiClient.get<AuthUser>('/api/auth/me'),
  })

  const createTeam = useMutation({
    mutationFn: (name: string) => apiClient.post<TeamInfo>('/api/teams', { name }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['teams'] }); setTeamName('') },
  })

  if (isLoading) return <p className="text-zinc-500 text-sm py-4">Loading…</p>
  if (error) return <p className="text-red-400 text-sm py-4">Failed to load teams.</p>

  const myTeamNames = me?.teams ?? []

  return (
    <div className="space-y-6">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-zinc-100 font-medium text-sm">Teams</h3>
        </div>
        {(teams ?? []).length === 0 ? (
          <p className="text-zinc-500 text-sm p-4">No teams yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-4 py-2 font-medium">Name</th>
                <th className="text-left px-4 py-2 font-medium">Members</th>
                <th className="text-left px-4 py-2 font-medium">Role</th>
              </tr>
            </thead>
            <tbody>
              {(teams ?? []).map(t => (
                <tr key={t.id} className="border-b border-zinc-800/50 last:border-0">
                  <td className="px-4 py-2 flex items-center gap-2">
                    <span className="text-zinc-100">{t.name}</span>
                    {myTeamNames.includes(t.name) && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30">you</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-zinc-400">{t.member_count}</td>
                  <td className="px-4 py-2">
                    {t.is_admin && (
                      <span className="text-xs px-2 py-0.5 rounded-full border bg-yellow-500/10 text-yellow-400 border-yellow-500/30">admin</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-zinc-100 font-medium text-sm mb-3">Create Team</h3>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-blue-500"
            placeholder="Team name"
            value={teamName}
            onChange={e => setTeamName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && teamName.trim() && createTeam.mutate(teamName.trim())}
          />
          <button
            onClick={() => teamName.trim() && createTeam.mutate(teamName.trim())}
            disabled={!teamName.trim() || createTeam.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
          >
            <Plus size={14} /> Create
          </button>
        </div>
        {createTeam.error && <p className="text-red-400 text-xs mt-2">{String(createTeam.error)}</p>}
      </div>
    </div>
  )
}

function TokensTab() {
  const qc = useQueryClient()
  const [tokenName, setTokenName] = useState('')
  const [newToken, setNewToken] = useState<APITokenCreated | null>(null)
  const [copied, setCopied] = useState(false)
  const [revokeId, setRevokeId] = useState<string | null>(null)
  const tokenRef = useRef<HTMLInputElement>(null)

  const { data: tokens, isLoading, error } = useQuery({
    queryKey: ['org-tokens'],
    queryFn: () => apiClient.get<APITokenInfo[]>('/api/org/tokens'),
  })

  const createToken = useMutation({
    mutationFn: (name: string) => apiClient.post<APITokenCreated>('/api/org/tokens', { name }),
    onSuccess: (data) => { qc.invalidateQueries({ queryKey: ['org-tokens'] }); setTokenName(''); setNewToken(data) },
  })

  const revokeToken = useMutation({
    mutationFn: (id: string) => apiClient.del<void>(`/api/org/tokens/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['org-tokens'] }); setRevokeId(null) },
  })

  function handleCopy() {
    if (!newToken) return
    navigator.clipboard.writeText(newToken.token).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (isLoading) return <p className="text-zinc-500 text-sm py-4">Loading…</p>
  if (error) return <p className="text-red-400 text-sm py-4">Failed to load tokens.</p>

  return (
    <div className="space-y-6">
      {newToken && (
        <div className="bg-green-500/5 border border-green-500/40 rounded-lg p-4 space-y-2">
          <p className="text-green-400 text-sm font-medium">Token created — copy it now, it won't be shown again.</p>
          <div className="flex gap-2 items-center">
            <input
              ref={tokenRef}
              readOnly
              value={newToken.token}
              onClick={() => tokenRef.current?.select()}
              className="flex-1 font-mono text-xs bg-zinc-900 border border-green-500/40 rounded px-3 py-1.5 text-green-300 cursor-pointer focus:outline-none select-all"
            />
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-100 text-sm rounded transition-colors"
            >
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              onClick={() => setNewToken(null)}
              className="text-zinc-500 hover:text-zinc-300 text-xs px-2 py-1.5"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-zinc-100 font-medium text-sm">API Tokens</h3>
        </div>
        {(tokens ?? []).length === 0 ? (
          <p className="text-zinc-500 text-sm p-4">No tokens yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-4 py-2 font-medium">Name</th>
                <th className="text-left px-4 py-2 font-medium">Created</th>
                <th className="text-left px-4 py-2 font-medium">Last Used</th>
                <th className="text-left px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {(tokens ?? []).map(t => (
                <tr key={t.id} className="border-b border-zinc-800/50 last:border-0">
                  <td className="px-4 py-2 text-zinc-100 font-mono text-xs">{t.name}</td>
                  <td className="px-4 py-2 text-zinc-400">{formatDate(t.created_at)}</td>
                  <td className="px-4 py-2 text-zinc-400">{formatDate(t.last_used_at)}</td>
                  <td className="px-4 py-2">
                    <span className={cn('text-xs px-2 py-0.5 rounded-full border',
                      t.revoked_at
                        ? 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30'
                        : 'bg-green-500/10 text-green-400 border-green-500/30'
                    )}>
                      {t.revoked_at ? 'revoked' : 'active'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {!t.revoked_at && (
                      revokeId === t.id ? (
                        <span className="inline-flex gap-2 items-center text-xs">
                          <span className="text-zinc-400">Confirm?</span>
                          <button
                            onClick={() => revokeToken.mutate(t.id)}
                            disabled={revokeToken.isPending}
                            className="text-red-400 hover:text-red-300 font-medium"
                          >
                            Yes
                          </button>
                          <button onClick={() => setRevokeId(null)} className="text-zinc-500 hover:text-zinc-300">No</button>
                        </span>
                      ) : (
                        <button
                          onClick={() => setRevokeId(t.id)}
                          className="flex items-center gap-1 text-red-500 hover:text-red-400 text-xs ml-auto"
                        >
                          <Trash2 size={13} /> Revoke
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-zinc-100 font-medium text-sm mb-3">Generate Token</h3>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-blue-500"
            placeholder="Token name"
            value={tokenName}
            onChange={e => setTokenName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && tokenName.trim() && createToken.mutate(tokenName.trim())}
          />
          <button
            onClick={() => tokenName.trim() && createToken.mutate(tokenName.trim())}
            disabled={!tokenName.trim() || createToken.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
          >
            <Plus size={14} /> Generate
          </button>
        </div>
        {createToken.error && <p className="text-red-400 text-xs mt-2">{String(createToken.error)}</p>}
      </div>
    </div>
  )
}

// --- Main export ---

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('org')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Settings</h1>
        <p className="text-sm text-zinc-500 mt-1">Manage your organization, teams, and API tokens</p>
      </div>

      <div className="flex gap-1 bg-zinc-800 p-1 rounded-lg w-fit">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'bg-blue-500 text-white'
                : 'text-zinc-400 hover:text-zinc-100'
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div>
        {activeTab === 'org'    && <OrgTab />}
        {activeTab === 'teams'  && <TeamsTab />}
        {activeTab === 'tokens' && <TokensTab />}
      </div>
    </div>
  )
}
