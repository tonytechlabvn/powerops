// Horizontal step progress bar for the wizard mode.
// Shows step pills with active/completed/pending states.

interface WizardStepIndicatorProps {
  steps: { id: string; label: string }[]
  currentStep: number
  onStepClick: (index: number) => void
}

export function WizardStepIndicator({ steps, currentStep, onStepClick }: WizardStepIndicatorProps) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-1">
      {steps.map((step, i) => {
        const isActive = i === currentStep
        const isCompleted = i < currentStep
        return (
          <button
            key={step.id}
            onClick={() => isCompleted && onStepClick(i)}
            disabled={!isCompleted && !isActive}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                        whitespace-nowrap transition-colors
                        ${isActive ? 'bg-blue-600 text-white' : ''}
                        ${isCompleted ? 'bg-green-900/40 text-green-400 cursor-pointer hover:bg-green-900/60' : ''}
                        ${!isActive && !isCompleted ? 'bg-zinc-800 text-zinc-500' : ''}`}
          >
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold
              ${isCompleted ? 'bg-green-600 text-white' : ''}
              ${isActive ? 'bg-white/20' : ''}
              ${!isActive && !isCompleted ? 'bg-zinc-700' : ''}`}>
              {isCompleted ? '\u2713' : i + 1}
            </span>
            {step.label}
          </button>
        )
      })}
    </div>
  )
}
