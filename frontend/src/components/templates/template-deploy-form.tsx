// Dynamic deploy form with beginner-friendly guidance for each variable

import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, HelpCircle, BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import { usePlanMutation } from '../../hooks/use-api'
import type { Template, TemplateVariable } from '../../types/api-types'
import { VARIABLE_GUIDES } from './variable-guides'

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
  const [showHelp, setShowHelp] = useState(false)
  const guide = VARIABLE_GUIDES[variable.name]
  const baseClass =
    'w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 placeholder-zinc-600'

  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1.5 text-sm font-medium text-zinc-300">
        {variable.name}
        {variable.required && <span className="text-red-400">*</span>}
        {guide && (
          <button
            type="button"
            onClick={() => setShowHelp(!showHelp)}
            className="text-zinc-500 hover:text-blue-400 transition-colors"
            title="Show help"
          >
            <HelpCircle size={14} />
          </button>
        )}
      </label>

      {variable.description && (
        <p className="text-xs text-zinc-500">{variable.description}</p>
      )}

      {/* Beginner help panel */}
      {showHelp && guide && (
        <div className="bg-blue-600/10 border border-blue-500/30 rounded-md p-3 space-y-2">
          <div className="flex items-start gap-2">
            <BookOpen size={14} className="text-blue-400 mt-0.5 shrink-0" />
            <div className="space-y-1.5">
              <p className="text-xs text-blue-300 font-medium">{guide.title}</p>
              <p className="text-xs text-zinc-300 leading-relaxed">{guide.explanation}</p>
              {guide.howToFind && (
                <div className="text-xs text-zinc-400">
                  <span className="text-yellow-400 font-medium">How to find it: </span>
                  {guide.howToFind}
                </div>
              )}
              {guide.examples && guide.examples.length > 0 && (
                <div className="text-xs text-zinc-400">
                  <span className="text-green-400 font-medium">Examples: </span>
                  {guide.examples.map((ex, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => onChange(ex)}
                      className="inline font-mono bg-zinc-800 px-1.5 py-0.5 rounded mr-1 mb-1 text-zinc-200 hover:bg-zinc-700 cursor-pointer transition-colors"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              )}
              {guide.warning && (
                <p className="text-xs text-red-300">⚠ {guide.warning}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {variable.type === 'bool' ? (
        <select className={baseClass} value={value} onChange={e => onChange(e.target.value)}>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      ) : (
        <input
          type={variable.type === 'number' ? 'number' : 'text'}
          className={baseClass}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={variable.default !== null ? String(variable.default) : guide?.examples?.[0] ?? ''}
        />
      )}
    </div>
  )
}

export function TemplateDeployForm({ template }: TemplateDeployFormProps) {
  const navigate = useNavigate()
  const planMutation = usePlanMutation()
  const [showAllHelp, setShowAllHelp] = useState(false)

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

  const hasGuides = template.variables.some(v => VARIABLE_GUIDES[v.name])

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Beginner tip banner */}
      <div className="bg-zinc-800 border border-zinc-700 rounded-md p-3 flex items-start gap-2">
        <BookOpen size={16} className="text-blue-400 mt-0.5 shrink-0" />
        <div className="text-xs text-zinc-400 space-y-1">
          <p className="text-zinc-200 font-medium">New to this? Click the <HelpCircle size={12} className="inline text-blue-400" /> icon next to any field for a beginner-friendly explanation.</p>
          <p>Fields marked with <span className="text-red-400">*</span> are required. Others have sensible defaults you can keep.</p>
        </div>
      </div>

      {hasGuides && (
        <button
          type="button"
          onClick={() => setShowAllHelp(!showAllHelp)}
          className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          {showAllHelp ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showAllHelp ? 'Hide all guides' : 'Show all guides'}
        </button>
      )}

      {template.variables.length === 0 ? (
        <p className="text-sm text-zinc-500">This template has no variables — ready to deploy!</p>
      ) : (
        template.variables.map(variable => (
          <VariableField
            key={variable.name}
            variable={variable}
            value={values[variable.name] ?? ''}
            onChange={v => setValue(variable.name, v)}
          />
        ))
      )}

      {error && (
        <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {error}
        </p>
      )}

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={planMutation.isPending}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium px-5 py-2.5 rounded-md transition-colors"
        >
          {planMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          {planMutation.isPending ? 'Deploying...' : 'Deploy & Plan'}
        </button>
        <span className="text-xs text-zinc-500">This will preview changes — nothing is created yet.</span>
      </div>
    </form>
  )
}
