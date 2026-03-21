// Auto Deploy panel: one-click EC2 deployment with smart defaults

import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Zap, Server } from 'lucide-react'
import { useAutoDeployMutation, useProviderConfig } from '../../hooks/use-api'

const INSTANCE_TYPES = ['t3.micro', 't3.small', 't3.medium', 't3.large']
const OS_OPTIONS = [
  { value: 'amazon-linux-2023', label: 'Amazon Linux 2023' },
  { value: 'ubuntu-22.04', label: 'Ubuntu 22.04 LTS' },
]

export function AutoDeployPanel() {
  const navigate = useNavigate()
  const mutation = useAutoDeployMutation()
  const { data: awsConfig } = useProviderConfig('aws')
  const [instanceName, setInstanceName] = useState('auto-web-server')
  const [instanceType, setInstanceType] = useState('t3.micro')
  const [osType, setOsType] = useState('amazon-linux-2023')
  const [error, setError] = useState<string | null>(null)

  const isConfigured = awsConfig?.configured ?? false

  async function handleDeploy(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!isConfigured) {
      setError('AWS credentials not configured. Go to Config page first.')
      return
    }

    try {
      const result = await mutation.mutateAsync({
        instance_name: instanceName.trim() || 'auto-web-server',
        instance_type: instanceType,
        os_type: osType,
        environment: 'dev',
      })
      navigate(`/jobs/${result.job_id}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Auto deploy failed'
      setError(msg)
    }
  }

  const selectClass =
    'w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500'
  const inputClass = selectClass

  return (
    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Zap size={18} className="text-emerald-400" />
        <h3 className="text-sm font-semibold text-emerald-400">Auto Deploy</h3>
      </div>
      <p className="text-xs text-zinc-400">
        Automatically detects the correct AMI for your region and generates an SSH key pair.
        No manual configuration needed.
      </p>

      <form onSubmit={handleDeploy} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-zinc-400">Instance Name</label>
            <input
              type="text"
              value={instanceName}
              onChange={e => setInstanceName(e.target.value)}
              placeholder="auto-web-server"
              className={inputClass}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-zinc-400">Instance Type</label>
            <select value={instanceType} onChange={e => setInstanceType(e.target.value)} className={selectClass}>
              {INSTANCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-zinc-400">Operating System</label>
          <select value={osType} onChange={e => setOsType(e.target.value)} className={selectClass}>
            {OS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="flex items-center gap-2 w-full justify-center bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2.5 rounded-md transition-colors"
        >
          {mutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Server size={14} />
          )}
          {mutation.isPending ? 'Deploying...' : 'Auto Deploy'}
        </button>
      </form>
    </div>
  )
}
