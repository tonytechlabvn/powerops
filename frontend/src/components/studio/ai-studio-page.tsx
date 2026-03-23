// AI Studio page — unified template creation hub with mode selector.
// Modes: Creator (NL→template), Extractor (HCL→template), Wizard (Phase 4), Canvas (Phase 5).

import { useState, useEffect, Component, type ReactNode, type ErrorInfo, lazy, Suspense } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import { useTemplateStudio } from '../../hooks/use-template-studio'
import { StudioCreatorPanel } from './studio-creator-panel'
import { StudioExtractorPanel } from './studio-extractor-panel'
import { StudioFilePreview } from './studio-file-preview'
import { StudioWizardPanel } from './wizard/studio-wizard-panel'
import type { StudioMode, StudioValidation } from '../../types/studio-types'

// Lazy-load canvas to isolate @xyflow/react from the main bundle
const StudioCanvasPanel = lazy(() =>
  import('./canvas/studio-canvas-panel').then(m => ({ default: m.StudioCanvasPanel }))
)

// Error boundary to catch canvas runtime crashes
class CanvasErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null }
  static getDerivedStateFromError(error: Error) { return { error } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('Canvas crash:', error, info) }
  render() {
    if (this.state.error) {
      return (
        <div className="flex items-center justify-center h-full bg-zinc-950 text-zinc-300 p-8">
          <div className="text-center max-w-md">
            <p className="text-red-400 font-semibold mb-2">Canvas failed to load</p>
            <pre className="text-xs text-zinc-500 whitespace-pre-wrap break-all">{this.state.error.message}</pre>
            <button onClick={() => this.setState({ error: null })}
              className="mt-4 px-4 py-2 bg-zinc-800 rounded hover:bg-zinc-700 text-sm">Retry</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

const MODES: { id: StudioMode; label: string }[] = [
  { id: 'creator', label: 'Creator' },
  { id: 'extractor', label: 'Extractor' },
  { id: 'wizard', label: 'Wizard' },
  { id: 'canvas', label: 'Canvas' },
]

export function AIStudioPage() {
  const [mode, setMode] = useState<StudioMode>('creator')
  const [editedFiles, setEditedFiles] = useState<Record<string, string>>({})
  const { state, generate, extract, refine, validate, save, load, reset } = useTemplateStudio()
  const params = useParams()
  const location = useLocation()

  // Load template for re-editing only when navigated to /studio/edit/{name}
  const isEditRoute = location.pathname.startsWith('/studio/edit/')
  const editName = isEditRoute ? params['*'] : undefined
  useEffect(() => {
    if (editName) {
      load(editName)
    }
  }, [editName, load])

  const currentFiles = Object.keys(editedFiles).length > 0
    ? editedFiles
    : (state.template?.files ?? {})

  const handleFileChange = (filename: string, content: string) => {
    setEditedFiles(prev => ({ ...prev, [filename]: content }))
  }

  const handleGenerate = async (description: string, providers: string[], complexity: string) => {
    const result = await generate(description, providers, complexity)
    if (result) { setEditedFiles({}); setManualValidation(null) }
  }

  const handleExtract = async (hclCode: string, templateName?: string) => {
    const result = await extract(hclCode, templateName)
    if (result) { setEditedFiles({}); setManualValidation(null) }
  }

  const handleRefine = async (refinement: string) => {
    if (!state.template) return
    const result = await refine(
      currentFiles,
      refinement,
      state.template.name,
      state.template.providers,
      state.template.description,
    )
    if (result) setEditedFiles({})
  }

  const handleSave = async () => {
    if (!state.template) return
    const name = state.template.name || prompt('Template name (e.g. aws/my-template):')
    if (!name) return
    await save(
      name,
      currentFiles,
      state.template.providers,
      false,
      state.template.description,
      state.template.display_name,
      state.template.tags,
    )
  }

  const [manualValidation, setManualValidation] = useState<StudioValidation | null>(null)

  const handleValidate = async () => {
    const result = await validate(currentFiles)
    if (result) setManualValidation(result)
  }

  // Use manual validation if available, otherwise template's built-in validation
  const activeValidation = manualValidation ?? state.template?.validation ?? null

  return (
    <div className="flex flex-col h-full bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">AI Studio</h1>
          <p className="text-zinc-500 text-sm mt-0.5">
            Create Jinja2 template packages from descriptions, HCL code, or visual canvas.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Mode selector */}
          <div className="flex bg-zinc-900 rounded-lg border border-zinc-700 p-0.5">
            {MODES.map(m => (
              <button
                key={m.id}
                onClick={() => { setMode(m.id); setEditedFiles({}) }}
                className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors
                  ${mode === m.id
                    ? 'bg-blue-600 text-white'
                    : 'text-zinc-400 hover:text-zinc-200'
                  }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          {state.template && (
            <button
              onClick={() => { reset(); setEditedFiles({}) }}
              className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200 border
                         border-zinc-700 rounded transition-colors"
            >
              Start Over
            </button>
          )}
        </div>
      </div>

      {/* Canvas mode: full-width layout */}
      {mode === 'canvas' ? (
        <div className="flex-1 overflow-hidden relative" style={{ minHeight: 0 }}>
          <CanvasErrorBoundary>
            <Suspense fallback={<div className="flex items-center justify-center h-full bg-zinc-950 text-zinc-500">Loading canvas...</div>}>
              <StudioCanvasPanel
                onGenerate={handleGenerate}
                isGenerating={state.status === 'generating'}
              />
            </Suspense>
          </CanvasErrorBoundary>
          {/* Show file preview overlay when template generated from canvas */}
          {state.template && Object.keys(currentFiles).length > 0 && (
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-zinc-950 border-t border-zinc-700 p-5 overflow-auto z-10">
              <StudioFilePreview
                files={currentFiles}
                validation={activeValidation}
                editable={true}
                onFileChange={handleFileChange}
                onSave={handleSave}
                providers={state.template?.providers}
                tags={state.template?.tags}
              />
            </div>
          )}
        </div>
      ) : (
        /* Two-panel layout for Creator/Extractor/Wizard */
        <div className="flex flex-1 overflow-hidden">
          {/* Left panel — mode-specific controls */}
          <div className="w-96 shrink-0 border-r border-zinc-800 flex flex-col overflow-y-auto p-5">
            {mode === 'creator' && (
              <StudioCreatorPanel
                template={state.template}
                status={state.status}
                error={state.error}
                chatHistory={state.chatHistory}
                onGenerate={handleGenerate}
                onRefine={handleRefine}
              />
            )}
            {mode === 'extractor' && (
              <StudioExtractorPanel
                template={state.template}
                status={state.status}
                error={state.error}
                chatHistory={state.chatHistory}
                onExtract={handleExtract}
                onRefine={handleRefine}
              />
            )}
            {mode === 'wizard' && (
              <StudioWizardPanel
                status={state.status}
                error={state.error}
                onGenerate={handleGenerate}
              />
            )}

            {/* Validate button */}
            {state.template && Object.keys(currentFiles).length > 0 && (
              <section className="border-t border-zinc-800 pt-5 mt-5">
                <button
                  onClick={handleValidate}
                  disabled={state.status === 'generating' || state.status === 'refining'}
                  className="w-full py-1.5 border border-zinc-600 text-zinc-300 text-sm
                             rounded hover:bg-zinc-800 disabled:opacity-40 transition-colors"
                >
                  Validate Template
                </button>
                {state.template.validation && (
                  <p className={`mt-2 text-xs font-medium text-center
                    ${state.template.validation.valid ? 'text-green-400' : 'text-red-400'}`}>
                    {state.template.validation.valid ? 'All files valid' : 'Validation errors found'}
                  </p>
                )}
              </section>
            )}
          </div>

          {/* Right panel — file preview */}
          <div className="flex-1 overflow-hidden p-5">
            <StudioFilePreview
              files={currentFiles}
              validation={activeValidation}
              editable={true}
              onFileChange={handleFileChange}
              onSave={state.template ? handleSave : undefined}
              providers={state.template?.providers}
              tags={state.template?.tags}
            />
          </div>
        </div>
      )}
    </div>
  )
}
