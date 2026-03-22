// Wizard review step — summary table of all step data + generate button.

interface WizardStepReviewProps {
  steps: { id: string; label: string }[]
  stepData: Record<string, Record<string, unknown>>
  onGenerate: () => void
  isGenerating: boolean
}

export function WizardStepReview({ steps, stepData, onGenerate, isGenerating }: WizardStepReviewProps) {
  // Filter out review step itself
  const dataSteps = steps.filter(s => s.id !== 'review')

  return (
    <div className="space-y-4">
      <p className="text-zinc-400 text-xs">Review your configuration before generating the template.</p>

      <div className="space-y-3">
        {dataSteps.map(step => {
          const data = stepData[step.id] ?? {}
          const entries = Object.entries(data).filter(([, v]) => v !== '' && v !== undefined)
          if (entries.length === 0) return null

          return (
            <div key={step.id} className="bg-zinc-900 rounded-lg border border-zinc-700 p-3">
              <h4 className="text-xs font-semibold text-zinc-300 mb-2">{step.label}</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {entries.map(([key, val]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="text-zinc-500">{key.replace(/_/g, ' ')}</span>
                    <span className="text-zinc-200 font-mono">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      <button
        onClick={onGenerate}
        disabled={isGenerating}
        className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                   text-white text-sm rounded-lg font-medium transition-colors"
      >
        {isGenerating ? 'Generating Template...' : 'Generate Template'}
      </button>
    </div>
  )
}
