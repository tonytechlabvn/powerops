// Wizard step: Provider selection — multi-provider chip selector.

interface WizardStepProviderProps {
  data: Record<string, unknown>
  defaults: Record<string, unknown>
  onChange: (data: Record<string, unknown>) => void
}

const ALL_PROVIDERS = ['aws', 'proxmox', 'azurerm', 'google']

export function WizardStepProvider({ data, defaults, onChange }: WizardStepProviderProps) {
  const providers = (data.providers ?? defaults.providers ?? ['aws']) as string[]

  const toggle = (p: string) => {
    const next = providers.includes(p) ? providers.filter(x => x !== p) : [...providers, p]
    onChange({ ...data, providers: next })
  }

  return (
    <div className="space-y-3">
      <p className="text-zinc-400 text-xs">Select the cloud providers for your template.</p>
      <div className="flex gap-2 flex-wrap">
        {ALL_PROVIDERS.map(p => (
          <button
            key={p}
            onClick={() => toggle(p)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border
              ${providers.includes(p)
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-200'}`}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}
