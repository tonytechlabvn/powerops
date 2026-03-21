// Policy management page: OPA Rego policies and policy sets
// Sections: policies list (with inline editor + test panel) and policy sets cards

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Shield, ShieldAlert, ShieldCheck, Plus, Trash2, Play,
  ChevronDown, ChevronRight, Loader2, CheckCircle, XCircle,
} from 'lucide-react'
import { apiClient } from '../../services/api-client'
import { cn, formatDate } from '../../lib/utils'
import type { PolicyInfo, PolicySetInfo, PolicyTestResult, PolicyEnforcement } from '../../types/api-types'

// ── Enforcement badge ────────────────────────────────────────────────────────

const ENFORCEMENT_META: Record<PolicyEnforcement, { label: string; cls: string; Icon: typeof Shield }> = {
  advisory:        { label: 'Advisory',       cls: 'bg-green-900/50 text-green-400 border-green-800',   Icon: ShieldCheck  },
  'soft-mandatory': { label: 'Soft Mandatory', cls: 'bg-yellow-900/50 text-yellow-400 border-yellow-800', Icon: Shield       },
  'hard-mandatory': { label: 'Hard Mandatory', cls: 'bg-red-900/50 text-red-400 border-red-800',         Icon: ShieldAlert  },
}

function EnforcementBadge({ level }: { level: PolicyEnforcement }) {
  const { label, cls, Icon } = ENFORCEMENT_META[level] ?? ENFORCEMENT_META.advisory
  return (
    <span className={cn('inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded border', cls)}>
      <Icon size={11} />
      {label}
    </span>
  )
}

// ── New-policy inline form ───────────────────────────────────────────────────

interface NewPolicyFormProps { onCancel: () => void; onSaved: () => void }

function NewPolicyForm({ onCancel, onSaved }: NewPolicyFormProps) {
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [enforcement, setEnforcement] = useState<PolicyEnforcement>('advisory')
  const [rego, setRego] = useState('package main\n\ndefault allow = true\n')
  const [err, setErr] = useState<string | null>(null)

  const mut = useMutation({
    mutationFn: () => apiClient.post('/api/policies', { name, description: desc, rego_code: rego, enforcement }),
    onSuccess: () => onSaved(),
    onError: (e: Error) => setErr(e.message),
  })

  return (
    <div className="border border-zinc-700 rounded-lg bg-zinc-900 p-4 space-y-3 mt-2">
      <h3 className="text-sm font-semibold text-zinc-200">New Policy</h3>
      <input
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600"
        placeholder="Policy name"
        value={name}
        onChange={e => setName(e.target.value)}
      />
      <input
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600"
        placeholder="Description (optional)"
        value={desc}
        onChange={e => setDesc(e.target.value)}
      />
      <select
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
        value={enforcement}
        onChange={e => setEnforcement(e.target.value as PolicyEnforcement)}
      >
        <option value="advisory">Advisory</option>
        <option value="soft-mandatory">Soft Mandatory</option>
        <option value="hard-mandatory">Hard Mandatory</option>
      </select>
      <textarea
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500 min-h-32 resize-y"
        placeholder="Rego policy code..."
        value={rego}
        onChange={e => setRego(e.target.value)}
      />
      {err && <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">{err}</p>}
      <div className="flex gap-2">
        <button
          onClick={() => mut.mutate()}
          disabled={!name.trim() || mut.isPending}
          className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
        >
          {mut.isPending && <Loader2 size={13} className="animate-spin" />}
          Save
        </button>
        <button onClick={onCancel} className="text-sm text-zinc-400 hover:text-zinc-200 px-4 py-2 rounded transition-colors">
          Cancel
        </button>
      </div>
    </div>
  )
}

// ── Test panel (shown inside expanded policy row) ────────────────────────────

function PolicyTestPanel({ policyId }: { policyId: string }) {
  const [planJson, setPlanJson] = useState('{\n  "resource_changes": []\n}')
  const [result, setResult] = useState<PolicyTestResult | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const testMut = useMutation({
    mutationFn: () => {
      let parsed: object
      try { parsed = JSON.parse(planJson) } catch { throw new Error('Invalid JSON in plan input') }
      return apiClient.post<PolicyTestResult>(`/api/policies/${policyId}/test`, { plan_json: parsed })
    },
    onSuccess: (data) => { setResult(data); setErr(null) },
    onError: (e: Error) => { setErr(e.message); setResult(null) },
  })

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-medium text-zinc-400">Test with sample plan JSON:</p>
      <textarea
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-blue-500 min-h-24 resize-y"
        value={planJson}
        onChange={e => setPlanJson(e.target.value)}
      />
      <button
        onClick={() => testMut.mutate()}
        disabled={testMut.isPending}
        className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 text-white text-xs font-medium px-3 py-1.5 rounded transition-colors"
      >
        {testMut.isPending ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
        Run Test
      </button>
      {err && <p className="text-xs text-red-400">{err}</p>}
      {result && (
        <div className="rounded border border-zinc-700 bg-zinc-800/50 p-3 space-y-2">
          <p className={cn('flex items-center gap-1.5 text-sm font-medium', result.passed ? 'text-green-400' : 'text-red-400')}>
            {result.passed ? <CheckCircle size={14} /> : <XCircle size={14} />}
            {result.passed ? 'All checks passed' : `${result.violations.length} violation(s)`}
          </p>
          {result.violations.map((v, i) => (
            <div key={i} className="text-xs bg-red-900/20 border border-red-800/40 rounded p-2">
              <span className="font-mono text-red-300">{v.resource}</span>
              <span className="text-zinc-400 mx-1">—</span>
              <span className="text-red-200">{v.message}</span>
            </div>
          ))}
          {result.warnings.map((w, i) => (
            <div key={i} className="text-xs bg-yellow-900/20 border border-yellow-800/40 rounded p-2">
              <span className="font-mono text-yellow-300">{w.resource}</span>
              <span className="text-zinc-400 mx-1">—</span>
              <span className="text-yellow-200">{w.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Policy row (expandable) ──────────────────────────────────────────────────

function PolicyRow({ policy, onDelete }: { policy: PolicyInfo; onDelete: (id: string) => void }) {
  const [open, setOpen] = useState(false)
  const [showTest, setShowTest] = useState(false)

  return (
    <>
      <tr
        className="border-b border-zinc-800 hover:bg-zinc-800/40 cursor-pointer transition-colors"
        onClick={() => { setOpen(o => !o); if (open) setShowTest(false) }}
      >
        <td className="px-4 py-3 w-6 text-zinc-500">
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </td>
        <td className="px-2 py-3 text-sm font-medium text-zinc-100">{policy.name}</td>
        <td className="px-2 py-3"><EnforcementBadge level={policy.enforcement} /></td>
        <td className="px-2 py-3 text-sm text-zinc-400 max-w-xs truncate">{policy.description || '—'}</td>
        <td className="px-2 py-3 text-xs text-zinc-500 whitespace-nowrap">{formatDate(policy.updated_at)}</td>
        <td className="px-2 py-3" onClick={e => e.stopPropagation()}>
          <button
            onClick={() => { if (confirm(`Delete policy "${policy.name}"?`)) onDelete(policy.id) }}
            className="text-zinc-600 hover:text-red-400 transition-colors p-1 rounded"
            title="Delete policy"
          >
            <Trash2 size={14} />
          </button>
        </td>
      </tr>
      {open && (
        <tr className="border-b border-zinc-800 bg-zinc-900/60">
          <td colSpan={6} className="px-6 py-4">
            <p className="text-xs font-medium text-zinc-400 mb-1">Rego Code</p>
            <pre className="bg-zinc-800 border border-zinc-700 rounded p-3 text-xs font-mono text-zinc-200 overflow-x-auto whitespace-pre-wrap">{policy.name}</pre>
            <button
              onClick={() => setShowTest(t => !t)}
              className="mt-3 flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              <Play size={12} /> {showTest ? 'Hide test panel' : 'Test this policy'}
            </button>
            {showTest && <PolicyTestPanel policyId={policy.id} />}
          </td>
        </tr>
      )}
    </>
  )
}

// ── New-set inline form ──────────────────────────────────────────────────────

function NewSetForm({ onCancel, onSaved }: { onCancel: () => void; onSaved: () => void }) {
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [scope, setScope] = useState('workspace')
  const [err, setErr] = useState<string | null>(null)

  const mut = useMutation({
    mutationFn: () => apiClient.post('/api/policy-sets', { name, description: desc, scope }),
    onSuccess: () => onSaved(),
    onError: (e: Error) => setErr(e.message),
  })

  return (
    <div className="border border-zinc-700 rounded-lg bg-zinc-900 p-4 space-y-3">
      <h3 className="text-sm font-semibold text-zinc-200">New Policy Set</h3>
      <input
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600"
        placeholder="Set name"
        value={name}
        onChange={e => setName(e.target.value)}
      />
      <input
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600"
        placeholder="Description (optional)"
        value={desc}
        onChange={e => setDesc(e.target.value)}
      />
      <select
        className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
        value={scope}
        onChange={e => setScope(e.target.value)}
      >
        <option value="workspace">Workspace</option>
        <option value="global">Global</option>
      </select>
      {err && <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">{err}</p>}
      <div className="flex gap-2">
        <button
          onClick={() => mut.mutate()}
          disabled={!name.trim() || mut.isPending}
          className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
        >
          {mut.isPending && <Loader2 size={13} className="animate-spin" />}
          Save
        </button>
        <button onClick={onCancel} className="text-sm text-zinc-400 hover:text-zinc-200 px-4 py-2 rounded transition-colors">
          Cancel
        </button>
      </div>
    </div>
  )
}

// ── Policy set card ──────────────────────────────────────────────────────────

function PolicySetCard({ set }: { set: PolicySetInfo }) {
  const scopeCls = set.scope === 'global'
    ? 'bg-blue-900/50 text-blue-400 border-blue-800'
    : 'bg-zinc-800 text-zinc-300 border-zinc-700'
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-zinc-100">{set.name}</p>
        <span className={cn('text-xs font-medium px-2 py-0.5 rounded border capitalize', scopeCls)}>{set.scope}</span>
      </div>
      {set.description && <p className="text-xs text-zinc-500">{set.description}</p>}
      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span>{set.policy_count} {set.policy_count === 1 ? 'policy' : 'policies'}</span>
        <span>{formatDate(set.created_at)}</span>
      </div>
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────

export function PolicyPage() {
  const qc = useQueryClient()
  const [showNewPolicy, setShowNewPolicy] = useState(false)
  const [showNewSet, setShowNewSet] = useState(false)

  const { data: policies, isLoading: polLoading, error: polError } = useQuery<PolicyInfo[]>({
    queryKey: ['policies'],
    queryFn: () => apiClient.get('/api/policies'),
  })

  const { data: policySets, isLoading: setLoading, error: setError } = useQuery<PolicySetInfo[]>({
    queryKey: ['policy-sets'],
    queryFn: () => apiClient.get('/api/policy-sets'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => apiClient.del(`/api/policies/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['policies'] }),
  })

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Policies</h1>
        <p className="text-sm text-zinc-500 mt-1">Manage OPA Rego policies and policy sets</p>
      </div>

      {/* Section 1: Policies */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-200 flex items-center gap-2">
            <Shield size={16} className="text-zinc-400" /> Policies
          </h2>
          {!showNewPolicy && (
            <button
              onClick={() => setShowNewPolicy(true)}
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-3 py-1.5 rounded transition-colors"
            >
              <Plus size={14} /> New Policy
            </button>
          )}
        </div>

        {showNewPolicy && (
          <NewPolicyForm
            onCancel={() => setShowNewPolicy(false)}
            onSaved={() => { setShowNewPolicy(false); qc.invalidateQueries({ queryKey: ['policies'] }) }}
          />
        )}

        <div className="rounded-lg border border-zinc-800 overflow-hidden">
          {polLoading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-zinc-500 text-sm">
              <Loader2 size={16} className="animate-spin" /> Loading policies...
            </div>
          ) : polError ? (
            <div className="py-10 text-center text-sm text-red-400">
              Failed to load policies: {(polError as Error).message}
            </div>
          ) : !policies?.length ? (
            <div className="py-10 text-center text-sm text-zinc-500">No policies defined yet.</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/80">
                  <th className="w-6" />
                  <th className="px-2 py-2.5 text-left text-xs font-medium text-zinc-400">Name</th>
                  <th className="px-2 py-2.5 text-left text-xs font-medium text-zinc-400">Enforcement</th>
                  <th className="px-2 py-2.5 text-left text-xs font-medium text-zinc-400">Description</th>
                  <th className="px-2 py-2.5 text-left text-xs font-medium text-zinc-400">Updated</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {policies.map(p => (
                  <PolicyRow key={p.id} policy={p} onDelete={id => deleteMut.mutate(id)} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* Section 2: Policy Sets */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-200 flex items-center gap-2">
            <ShieldCheck size={16} className="text-zinc-400" /> Policy Sets
          </h2>
          {!showNewSet && (
            <button
              onClick={() => setShowNewSet(true)}
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-3 py-1.5 rounded transition-colors"
            >
              <Plus size={14} /> New Set
            </button>
          )}
        </div>

        {showNewSet && (
          <NewSetForm
            onCancel={() => setShowNewSet(false)}
            onSaved={() => { setShowNewSet(false); qc.invalidateQueries({ queryKey: ['policy-sets'] }) }}
          />
        )}

        {setLoading ? (
          <div className="flex items-center justify-center gap-2 py-10 text-zinc-500 text-sm">
            <Loader2 size={16} className="animate-spin" /> Loading policy sets...
          </div>
        ) : setError ? (
          <div className="py-8 text-center text-sm text-red-400">
            Failed to load policy sets: {(setError as Error).message}
          </div>
        ) : !policySets?.length ? (
          <div className="py-8 text-center text-sm text-zinc-500">No policy sets defined yet.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {policySets.map(s => <PolicySetCard key={s.id} set={s} />)}
          </div>
        )}
      </section>
    </div>
  )
}
