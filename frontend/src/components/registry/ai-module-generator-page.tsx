// AI Module Generator page — multi-step wizard: describe → generate → refine → validate.
// Two-panel layout: left prompt/controls, right generated file preview.

import { useState } from 'react'
import { useModuleGenerator } from '../../hooks/use-module-generator'
import { ModuleFilePreviewTabs } from './module-file-preview-tabs'

type Step = 'describe' | 'review' | 'refine'

const PROVIDERS = ['aws', 'azurerm', 'google', 'proxmox']
const COMPLEXITIES = [
  { value: 'simple',   label: 'Simple',   hint: 'Single resource, 3–5 variables' },
  { value: 'standard', label: 'Standard', hint: '3–8 resources, full outputs' },
  { value: 'complex',  label: 'Complex',  hint: 'Multi-resource, lifecycle rules' },
]

export function AIModuleGeneratorPage() {
  const [step, setStep] = useState<Step>('describe')
  const [description, setDescription] = useState('')
  const [provider, setProvider] = useState('aws')
  const [complexity, setComplexity] = useState('standard')
  const [refinement, setRefinement] = useState('')
  const [editedFiles, setEditedFiles] = useState<Record<string, string>>({})

  const { state, generate, refine, validate } = useModuleGenerator()

  const currentFiles = Object.keys(editedFiles).length > 0
    ? editedFiles
    : (state.module?.files ?? {})

  const handleGenerate = async () => {
    if (!description.trim()) return
    const result = await generate(description, provider, complexity)
    if (result) {
      setEditedFiles({})
      setStep('review')
    }
  }

  const handleRefine = async () => {
    if (!refinement.trim() || !currentFiles) return
    const name = state.module?.name ?? ''
    const desc = state.module?.description ?? description
    const result = await refine(currentFiles, refinement, name, provider, desc)
    if (result) {
      setEditedFiles({})
      setRefinement('')
    }
  }

  const handleValidate = async () => {
    if (!currentFiles) return
    await validate(currentFiles)
  }

  const handleFileChange = (filename: string, content: string) => {
    setEditedFiles(prev => ({ ...prev, filename, [filename]: content }))
  }

  const isGenerating = state.status === 'generating'

  return (
    <div className="flex flex-col h-full bg-zinc-950 text-zinc-100">
      {/* Page header */}
      <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">AI Module Generator</h1>
          <p className="text-zinc-500 text-sm mt-0.5">
            Describe your infrastructure in plain English — AI generates a complete Terraform module.
          </p>
        </div>
        {step !== 'describe' && (
          <button
            onClick={() => { setStep('describe'); setEditedFiles({}) }}
            className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200 border
                       border-zinc-700 rounded transition-colors"
          >
            ← Start Over
          </button>
        )}
      </div>

      {/* Two-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel — controls */}
        <div className="w-96 shrink-0 border-r border-zinc-800 flex flex-col overflow-y-auto p-5 gap-5">

          {/* Step 1: Describe */}
          <section>
            <h2 className="text-sm font-semibold text-zinc-300 mb-3">
              1. Describe Requirements
            </h2>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="e.g. Create an AWS VPC module with public and private subnets, NAT gateway, and VPC flow logs enabled."
              rows={5}
              disabled={isGenerating}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                         text-zinc-100 text-sm resize-none placeholder-zinc-500
                         focus:outline-none focus:border-blue-500 disabled:opacity-50"
            />

            {/* Provider selector */}
            <div className="mt-3">
              <label className="text-zinc-400 text-xs font-medium block mb-1.5">Provider</label>
              <div className="flex gap-2 flex-wrap">
                {PROVIDERS.map(p => (
                  <button
                    key={p}
                    onClick={() => setProvider(p)}
                    disabled={isGenerating}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors
                      ${provider === p
                        ? 'bg-blue-600 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:text-zinc-200'
                      } disabled:opacity-50`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Complexity selector */}
            <div className="mt-3">
              <label className="text-zinc-400 text-xs font-medium block mb-1.5">Complexity</label>
              <div className="space-y-1.5">
                {COMPLEXITIES.map(c => (
                  <button
                    key={c.value}
                    onClick={() => setComplexity(c.value)}
                    disabled={isGenerating}
                    className={`w-full text-left px-3 py-2 rounded border text-xs transition-colors
                      ${complexity === c.value
                        ? 'border-blue-500 bg-blue-950/30 text-zinc-100'
                        : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600'
                      } disabled:opacity-50`}
                  >
                    <span className="font-medium">{c.label}</span>
                    <span className="text-zinc-500 ml-2">{c.hint}</span>
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleGenerate}
              disabled={isGenerating || !description.trim()}
              className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                         text-white text-sm rounded font-medium transition-colors"
            >
              {isGenerating ? 'Generating…' : step === 'describe' ? 'Generate Module' : 'Regenerate'}
            </button>
          </section>

          {/* Step 2+: Refinement */}
          {step !== 'describe' && (
            <section className="border-t border-zinc-800 pt-5">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3">
                2. Refine
              </h2>
              <textarea
                value={refinement}
                onChange={e => setRefinement(e.target.value)}
                placeholder="e.g. Add a VPC endpoint for S3, enable DNS hostnames, add lifecycle rules."
                rows={3}
                disabled={isGenerating}
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                           text-zinc-100 text-sm resize-none placeholder-zinc-500
                           focus:outline-none focus:border-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleRefine}
                disabled={isGenerating || !refinement.trim()}
                className="mt-2 w-full py-1.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40
                           text-white text-sm rounded font-medium transition-colors"
              >
                {isGenerating ? 'Refining…' : 'Apply Refinement'}
              </button>
            </section>
          )}

          {/* Validate button */}
          {step !== 'describe' && Object.keys(currentFiles).length > 0 && (
            <section className="border-t border-zinc-800 pt-5">
              <button
                onClick={handleValidate}
                disabled={isGenerating}
                className="w-full py-1.5 border border-zinc-600 text-zinc-300 text-sm
                           rounded hover:bg-zinc-800 disabled:opacity-40 transition-colors"
              >
                Validate HCL
              </button>
              {state.module?.validation && (
                <p className={`mt-2 text-xs font-medium text-center
                  ${state.module.validation.valid ? 'text-green-400' : 'text-red-400'}`}>
                  {state.module.validation.valid ? '✓ All files valid' : '✕ Validation errors found'}
                </p>
              )}
            </section>
          )}

          {state.error && (
            <p className="text-red-400 text-xs">{state.error}</p>
          )}
        </div>

        {/* Right panel — file preview */}
        <div className="flex-1 overflow-hidden p-5">
          {Object.keys(currentFiles).length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-zinc-600 gap-3">
              <span className="text-5xl">⚡</span>
              <p className="text-sm">Generated module files will appear here.</p>
            </div>
          ) : (
            <ModuleFilePreviewTabs
              files={currentFiles}
              validation={state.module?.validation ?? null}
              editable={true}
              onFileChange={handleFileChange}
            />
          )}

          {/* Module metadata bar */}
          {state.module && (
            <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
              <span>Provider: <span className="text-zinc-300">{state.module.provider}</span></span>
              <span>Files: <span className="text-zinc-300">{Object.keys(currentFiles).length}</span></span>
              {state.module.resources.length > 0 && (
                <span>
                  Resources:{' '}
                  <span className="text-zinc-300">{state.module.resources.join(', ')}</span>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
