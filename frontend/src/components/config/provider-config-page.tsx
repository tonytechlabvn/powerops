// Provider configuration page: AWS and Proxmox credential forms

import { useState } from 'react'
import type { FormEvent } from 'react'
import { Loader2, CheckCircle } from 'lucide-react'
import { useSaveProviderConfig } from '../../hooks/use-api'
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
  const [values, setValues] = useState<Record<string, string>>(
    () => Object.fromEntries(fields.map(f => [f.key, '']))
  )
  const [saved, setSaved] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const saveMutation = useSaveProviderConfig()

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
      // Clear password fields after save
      setValues(prev => {
        const next = { ...prev }
        fields.filter(f => f.type === 'password').forEach(f => { next[f.key] = '' })
        return next
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : typeof err === 'string' ? err : 'Save failed'
      setFormError(msg)
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 space-y-5">
      <div>
        <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
        <p className="text-sm text-zinc-500 mt-1">{description}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {fields.map(field => (
          <div key={field.key} className="space-y-1">
            <label className="text-sm font-medium text-zinc-300">{field.label}</label>
            <input
              type={field.type}
              value={values[field.key]}
              onChange={e => setValue(field.key, e.target.value)}
              placeholder={field.placeholder}
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
          Save Configuration
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
