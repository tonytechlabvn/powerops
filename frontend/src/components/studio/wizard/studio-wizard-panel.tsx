// Wizard mode panel — AI-driven step-by-step form for structured template creation.
// Initial description → AI determines steps → user fills forms → generate template.

import { useState } from 'react'
import { apiClient } from '../../../services/api-client'
import { WizardStepIndicator } from './wizard-step-indicator'
import { WizardStepProvider } from './wizard-step-provider'
import { WizardStepReview } from './wizard-step-review'
import {
  WizardStepFields,
  COMPUTE_FIELDS,
  NETWORKING_FIELDS,
  STORAGE_FIELDS,
  SECURITY_FIELDS,
  CONNECTIVITY_FIELDS,
  MONITORING_FIELDS,
} from './wizard-step-fields'
import type { StudioStatus } from '../../../types/studio-types'

// Step ID → label mapping
const STEP_LABELS: Record<string, string> = {
  provider: 'Providers',
  compute: 'Compute',
  networking: 'Networking',
  storage: 'Storage',
  security: 'Security',
  connectivity: 'Connectivity',
  monitoring: 'Monitoring',
  review: 'Review & Generate',
}

// Step ID → description
const STEP_DESCRIPTIONS: Record<string, string> = {
  compute: 'Configure compute resources — instances, VMs, and containers.',
  networking: 'Define network topology — VPC, subnets, gateways.',
  storage: 'Set up storage — volumes, buckets, and pools.',
  security: 'Configure security — IAM, firewall rules, encryption.',
  connectivity: 'Set up connectivity — VPN, peering, cross-provider links.',
  monitoring: 'Configure monitoring — alerts, logs, dashboards.',
}

// Step ID → field definitions
const STEP_FIELD_MAP: Record<string, typeof COMPUTE_FIELDS> = {
  compute: COMPUTE_FIELDS,
  networking: NETWORKING_FIELDS,
  storage: STORAGE_FIELDS,
  security: SECURITY_FIELDS,
  connectivity: CONNECTIVITY_FIELDS,
  monitoring: MONITORING_FIELDS,
}

interface StudioWizardPanelProps {
  status: StudioStatus
  error: string | null
  onGenerate: (description: string, providers: string[], complexity: string, context?: string) => void
}

interface WizardAnalysis {
  steps: string[]
  defaults: Record<string, Record<string, unknown>>
  reasoning: string
}

export function StudioWizardPanel({ status, error, onGenerate }: StudioWizardPanelProps) {
  const [description, setDescription] = useState('')
  const [analysis, setAnalysis] = useState<WizardAnalysis | null>(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [stepData, setStepData] = useState<Record<string, Record<string, unknown>>>({})
  const [analyzing, setAnalyzing] = useState(false)

  const handleAnalyze = async () => {
    if (!description.trim()) return
    setAnalyzing(true)
    try {
      const result = await apiClient.post<WizardAnalysis>('/api/ai/studio/wizard-steps', {
        description,
      })
      setAnalysis(result)
      setCurrentStep(0)
      // Pre-fill step data with AI defaults
      const initialData: Record<string, Record<string, unknown>> = {}
      for (const stepId of result.steps) {
        initialData[stepId] = result.defaults[stepId] ?? {}
      }
      setStepData(initialData)
    } catch {
      // Fallback to basic steps
      setAnalysis({ steps: ['provider', 'review'], defaults: {}, reasoning: 'Analysis failed' })
    } finally {
      setAnalyzing(false)
    }
  }

  const handleStepDataChange = (stepId: string, data: Record<string, unknown>) => {
    setStepData(prev => ({ ...prev, [stepId]: data }))
  }

  const handleGenerateFromWizard = () => {
    // Assemble structured context from step data
    const providers = (stepData.provider?.providers as string[]) ?? ['aws']
    const context = JSON.stringify(stepData, null, 2)
    onGenerate(description, providers, 'complex', context)
  }

  const isWorking = status === 'generating' || analyzing

  // Phase 1: description input
  if (!analysis) {
    return (
      <div className="flex flex-col gap-5">
        <section>
          <h2 className="text-sm font-semibold text-zinc-300 mb-3">Describe Your Infrastructure</h2>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="e.g. WireGuard VPN between AWS EC2 and Proxmox VM with monitoring..."
            rows={5}
            disabled={isWorking}
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                       text-zinc-100 text-sm resize-none placeholder-zinc-500
                       focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleAnalyze}
            disabled={isWorking || !description.trim()}
            className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                       text-white text-sm rounded font-medium transition-colors"
          >
            {analyzing ? 'Analyzing...' : 'Analyze & Build Wizard'}
          </button>
        </section>
        {error && <p className="text-red-400 text-xs">{error}</p>}
      </div>
    )
  }

  // Phase 2: wizard steps
  const steps = analysis.steps.map(id => ({ id, label: STEP_LABELS[id] ?? id }))
  const activeStepId = analysis.steps[currentStep]
  const activeDefaults = analysis.defaults[activeStepId] ?? {}
  const activeData = stepData[activeStepId] ?? {}

  return (
    <div className="flex flex-col gap-4">
      {/* Reasoning */}
      {analysis.reasoning && (
        <p className="text-zinc-500 text-xs italic bg-zinc-900/50 rounded px-3 py-2">
          {analysis.reasoning}
        </p>
      )}

      {/* Step indicator */}
      <WizardStepIndicator
        steps={steps}
        currentStep={currentStep}
        onStepClick={setCurrentStep}
      />

      {/* Active step content */}
      <div className="min-h-[200px]">
        {activeStepId === 'provider' && (
          <WizardStepProvider
            data={activeData}
            defaults={activeDefaults}
            onChange={d => handleStepDataChange('provider', d)}
          />
        )}
        {activeStepId === 'review' && (
          <WizardStepReview
            steps={steps}
            stepData={stepData}
            onGenerate={handleGenerateFromWizard}
            isGenerating={status === 'generating'}
          />
        )}
        {activeStepId !== 'provider' && activeStepId !== 'review' && STEP_FIELD_MAP[activeStepId] && (
          <WizardStepFields
            fields={STEP_FIELD_MAP[activeStepId]}
            data={activeData}
            defaults={activeDefaults}
            onChange={d => handleStepDataChange(activeStepId, d)}
            description={STEP_DESCRIPTIONS[activeStepId]}
          />
        )}
      </div>

      {/* Navigation */}
      <div className="flex gap-2 pt-2 border-t border-zinc-800">
        {currentStep > 0 && (
          <button
            onClick={() => setCurrentStep(s => s - 1)}
            className="px-4 py-1.5 bg-zinc-800 text-zinc-300 text-xs rounded
                       hover:bg-zinc-700 transition-colors"
          >
            Back
          </button>
        )}
        {currentStep < steps.length - 1 && (
          <button
            onClick={() => setCurrentStep(s => s + 1)}
            className="px-4 py-1.5 bg-blue-600 text-white text-xs rounded
                       hover:bg-blue-500 transition-colors ml-auto"
          >
            Next
          </button>
        )}
        <button
          onClick={() => { setAnalysis(null); setStepData({}) }}
          className="px-3 py-1.5 text-zinc-500 text-xs hover:text-zinc-300 transition-colors ml-auto"
        >
          Start Over
        </button>
      </div>

      {error && <p className="text-red-400 text-xs">{error}</p>}
    </div>
  )
}
