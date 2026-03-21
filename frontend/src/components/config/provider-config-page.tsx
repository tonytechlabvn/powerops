// Provider configuration page: AWS and Proxmox credential forms

import { useState } from 'react'
import type { FormEvent } from 'react'
import { Loader2, CheckCircle, ShieldCheck } from 'lucide-react'
import { useSaveProviderConfig, useProviderConfig } from '../../hooks/use-api'
import type { ProviderConfig } from '../../types/api-types'

interface FieldDef {
  key: string
  label: string
  type: 'text' | 'password'
  placeholder?: string
}

interface ProviderFormProps {
  provider: string
  title: string
  description: string
  fields: FieldDef[]
}

function ProviderForm({ provider, title, description, fields }: ProviderFormProps) {
  const { data: existing } = useProviderConfig(provider)
  const [values, setValues] = useState<Record<string, string>>(
    () => Object.fromEntries(fields.map(f => [f.key, '']))
  )
  const [saved, setSaved] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const saveMutation = useSaveProviderConfig()

  const isConfigured = existing?.configured ?? false
  const configuredKeys = existing?.credentials_redacted
    ? Object.keys(existing.credentials_redacted)
    : []

  function setValue(key: string, value: string) {
    setValues(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    setSaved(false)

    // Only send non-empty values
    const config: Record<string, string> = {}
    fields.forEach(f => {
      if (values[f.key]?.trim()) config[f.key] = values[f.key].trim()
    })

    if (Object.keys(config).length === 0) {
      setFormError('Please fill in at least one field.')
      return
    }

    const payload: ProviderConfig = { provider, config }
    try {
      await saveMutation.mutateAsync(payload)
      setSaved(true)
      // Clear all fields after save (values are persisted server-side)
      setValues(Object.fromEntries(fields.map(f => [f.key, ''])))
    } catch (err) {
      const msg = err instanceof Error ? err.message : typeof err === 'string' ? err : 'Save failed'
      setFormError(msg)
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
          <p className="text-sm text-zinc-500 mt-1">{description}</p>
        </div>
        {isConfigured && (
          <span className="flex items-center gap-1.5 text-xs font-medium text-green-400 bg-green-500/10 border border-green-500/30 rounded-full px-3 py-1">
            <ShieldCheck size={14} /> Configured
          </span>
        )}
      </div>

      {isConfigured && (
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-md p-3 space-y-1">
          <p className="text-xs text-zinc-400 font-medium">Saved credentials:</p>
          {configuredKeys.map(key => (
            <div key={key} className="flex items-center gap-2 text-xs">
              <span className="text-zinc-300 font-mono">{key}</span>
              <span className="text-zinc-600">= ***</span>
            </div>
          ))}
          <p className="text-xs text-zinc-500 mt-2">Enter new values below to update.</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {fields.map(field => (
          <div key={field.key} className="space-y-1">
            <label className="flex items-center gap-2 text-sm font-medium text-zinc-300">
              {field.label}
              {configuredKeys.includes(field.key) && (
                <CheckCircle size={12} className="text-green-500" />
              )}
            </label>
            <input
              type={field.type}
              value={values[field.key]}
              onChange={e => setValue(field.key, e.target.value)}
              placeholder={configuredKeys.includes(field.key) ? '••• (saved, enter to update)' : field.placeholder}
              autoComplete={field.type === 'password' ? 'new-password' : 'off'}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600"
            />
          </div>
        ))}

        {formError && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
            {formError}
          </p>
        )}

        {saved && (
          <p className="flex items-center gap-2 text-sm text-green-400">
            <CheckCircle size={14} /> Configuration saved
          </p>
        )}

        <button
          type="submit"
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
        >
          {saveMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          {isConfigured ? 'Update Configuration' : 'Save Configuration'}
        </button>
      </form>
    </div>
  )
}

const AWS_FIELDS: FieldDef[] = [
  { key: 'aws_access_key_id',     label: 'Access Key ID',     type: 'text',     placeholder: 'AKIAIOSFODNN7EXAMPLE' },
  { key: 'aws_secret_access_key', label: 'Secret Access Key', type: 'password', placeholder: '••••••••••••••••••••' },
  { key: 'aws_region',            label: 'Default Region',    type: 'text',     placeholder: 'us-east-1' },
]

const PROXMOX_FIELDS: FieldDef[] = [
  { key: 'proxmox_api_url',      label: 'API URL',      type: 'text',     placeholder: 'https://proxmox.example.com:8006' },
  { key: 'proxmox_user',         label: 'User',         type: 'text',     placeholder: 'root@pam' },
  { key: 'proxmox_password',     label: 'Password',     type: 'password', placeholder: '••••••••' },
  { key: 'proxmox_tls_insecure', label: 'TLS Insecure', type: 'text',     placeholder: 'false' },
]

export function ProviderConfigPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Configuration</h1>
        <p className="text-sm text-zinc-500 mt-1">Manage provider credentials and settings</p>
      </div>

      <ProviderForm
        provider="aws"
        title="AWS"
        description="Configure AWS credentials for Terraform AWS provider"
        fields={AWS_FIELDS}
      />

      <ProviderForm
        provider="proxmox"
        title="Proxmox"
        description="Configure Proxmox VE credentials for Terraform Proxmox provider"
        fields={PROXMOX_FIELDS}
      />
    </div>
  )
}
