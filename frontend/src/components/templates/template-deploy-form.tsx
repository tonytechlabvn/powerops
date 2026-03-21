// Dynamic deploy form built from template variable schema

import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { usePlanMutation } from '../../hooks/use-api'
import type { Template, TemplateVariable } from '../../types/api-types'

interface TemplateDeployFormProps {
  template: Template
}

function VariableField({
  variable,
  value,
  onChange,
}: {
  variable: TemplateVariable
  value: string
  onChange: (v: string) => void
}) {
  const baseClass =
    'w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600'

  if (variable.type === 'bool') {
    return (
      <select className={baseClass} value={value} onChange={e => onChange(e.target.value)}>
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
    )
  }

  return (
    <input
      type={variable.type === 'number' ? 'number' : 'text'}
      className={baseClass}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={variable.default !== null ? String(variable.default) : undefined}
    />
  )
}

export function TemplateDeployForm({ template }: TemplateDeployFormProps) {
  const navigate = useNavigate()
  const planMutation = usePlanMutation()

  // Initialize form state from variable defaults
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    template.variables.forEach(v => {
      init[v.name] = v.default !== null ? String(v.default) : ''
    })
    return init
  })
  const [error, setError] = useState<string | null>(null)

  function setValue(name: string, value: string) {
    setValues(prev => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    // Validate required fields
    const missing = template.variables
      .filter(v => v.required && !values[v.name]?.trim())
      .map(v => v.name)

    if (missing.length > 0) {
      setError(`Required fields missing: ${missing.join(', ')}`)
      return
    }

    try {
      const result = await planMutation.mutateAsync({
        template: template.name,
        variables: values,
      })
      navigate(`/jobs/${result.job_id}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : typeof err === 'string' ? err : 'Failed to start deployment'
      setError(msg)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {template.variables.length === 0 ? (
        <p className="text-sm text-zinc-500">This template has no variables.</p>
      ) : (
        template.variables.map(variable => (
          <div key={variable.name} className="space-y-1">
            <label className="flex items-center gap-1.5 text-sm font-medium text-zinc-300">
              {variable.name}
              {variable.required && <span className="text-red-400">*</span>}
            </label>
            {variable.description && (
              <p className="text-xs text-zinc-500">{variable.description}</p>
            )}
            <VariableField
              variable={variable}
              value={values[variable.name] ?? ''}
              onChange={v => setValue(variable.name, v)}
            />
          </div>
        ))
      )}

      {error && (
        <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={planMutation.isPending}
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
      >
        {planMutation.isPending && <Loader2 size={14} className="animate-spin" />}
        {planMutation.isPending ? 'Deploying...' : 'Deploy & Plan'}
      </button>
    </form>
  )
}
