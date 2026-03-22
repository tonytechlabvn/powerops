// KB lab page: HCL editor + validation panel, level selector, hints, complete chapter

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ChevronRight, ChevronDown, Lightbulb, CheckCircle, FlaskConical } from 'lucide-react'
import { useKBLab, useValidateLab, useCompleteChapter } from '../../hooks/use-kb'
import { KBLabEditor } from './kb-lab-editor'
import { KBValidationResult } from './kb-validation-result'
import type { LabValidationResult } from '../../types/kb-types'

export function KBLabPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  const { data: lab, isLoading, error } = useKBLab(slug)
  const validateLab = useValidateLab()
  const completeChapter = useCompleteChapter()

  const [hcl, setHcl] = useState<string>('')
  const [level, setLevel] = useState<string>('')
  const [result, setResult] = useState<LabValidationResult | null>(null)
  const [hintsShown, setHintsShown] = useState(0)
  const [instructionsOpen, setInstructionsOpen] = useState(true)
  const [completed, setCompleted] = useState(false)

  // Seed editor with starter HCL once lab loads
  if (lab && hcl === '') {
    setHcl(lab.starter_hcl)
    setLevel(lab.recommended_level)
  }

  async function handleValidate() {
    try {
      const res = await validateLab.mutateAsync({ slug, hcl, level })
      setResult(res)
    } catch {
      // error surfaced via mutation state
    }
  }

  async function handleComplete() {
    try {
      await completeChapter.mutateAsync(slug)
      setCompleted(true)
    } catch {
      // error surfaced via mutation state
    }
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-zinc-500">Loading lab...</div>
  }
  if (error || !lab) {
    return <div className="flex items-center justify-center h-64 text-red-400">Failed to load lab.</div>
  }

  const hints = lab.hints ?? []
  const canShowMoreHints = hintsShown < hints.length

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <Link to="/kb" className="hover:text-zinc-300 transition-colors">Knowledge Base</Link>
        <ChevronRight size={12} />
        <Link to={`/kb/${slug}`} className="hover:text-zinc-300 transition-colors capitalize">
          {slug.replace(/-/g, ' ')}
        </Link>
        <ChevronRight size={12} />
        <span className="text-zinc-300">Lab</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FlaskConical size={18} className="text-blue-400" />
            <h1 className="text-xl font-bold text-zinc-100">{lab.title}</h1>
          </div>
          <p className="text-zinc-400 text-sm">{lab.description}</p>
        </div>
        {completed && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/30 rounded-md text-green-400 text-sm">
            <CheckCircle size={15} /> Chapter Completed
          </div>
        )}
      </div>

      {/* Collapsible instructions */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <button
          onClick={() => setInstructionsOpen((o) => !o)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-zinc-300 hover:bg-zinc-800 transition-colors"
        >
          <span>Instructions</span>
          <ChevronDown
            size={15}
            className={`transition-transform ${instructionsOpen ? 'rotate-180' : ''}`}
          />
        </button>
        {instructionsOpen && (
          <div className="px-4 pb-4 text-sm text-zinc-400 leading-relaxed whitespace-pre-wrap border-t border-zinc-800 pt-3">
            {lab.instructions}
          </div>
        )}
      </div>

      {/* Level selector */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-zinc-500 font-medium">Validation level:</span>
        {lab.available_levels.map((lvl) => (
          <button
            key={lvl}
            onClick={() => setLevel(lvl)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
              level === lvl
                ? 'border-blue-500 bg-blue-500/10 text-blue-300'
                : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'
            }`}
          >
            {lvl}
            {lvl === lab.recommended_level && (
              <span className="text-yellow-400 text-[10px]">recommended</span>
            )}
          </button>
        ))}
      </div>

      {/* Editor + validation panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-2">
          <p className="text-xs text-zinc-500 font-medium">HCL Editor</p>
          <KBLabEditor value={hcl} onChange={setHcl} />
        </div>
        <div className="space-y-2">
          <p className="text-xs text-zinc-500 font-medium">Validation Results</p>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 min-h-[400px]">
            <KBValidationResult result={result} isLoading={validateLab.isPending} />
          </div>
        </div>
      </div>

      {/* Hints */}
      {hints.length > 0 && (
        <div className="space-y-2">
          {hints.slice(0, hintsShown).map((hint, i) => (
            <div key={i} className="flex items-start gap-2 px-3 py-2 bg-yellow-500/5 border border-yellow-500/20 rounded-md text-sm text-yellow-300">
              <Lightbulb size={14} className="shrink-0 mt-0.5 text-yellow-400" />
              <span>{hint}</span>
            </div>
          ))}
          {canShowMoreHints && (
            <button
              onClick={() => setHintsShown((n) => n + 1)}
              className="flex items-center gap-2 text-xs text-yellow-400 hover:text-yellow-300 transition-colors"
            >
              <Lightbulb size={13} /> Show hint {hintsShown + 1} of {hints.length}
            </button>
          )}
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center gap-3 pt-2 border-t border-zinc-800">
        <button
          onClick={handleValidate}
          disabled={validateLab.isPending || !hcl.trim()}
          className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
        >
          {validateLab.isPending ? 'Validating...' : 'Validate'}
        </button>

        {result?.passed && !completed && (
          <button
            onClick={handleComplete}
            disabled={completeChapter.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-green-600 hover:bg-green-500 disabled:opacity-40 text-white text-sm font-medium transition-colors"
          >
            <CheckCircle size={15} />
            {completeChapter.isPending ? 'Saving...' : 'Complete Chapter'}
          </button>
        )}

        {validateLab.isError && (
          <p className="text-red-400 text-xs">Validation failed — please try again.</p>
        )}
        {completeChapter.isError && (
          <p className="text-red-400 text-xs">Could not save completion — please try again.</p>
        )}
      </div>
    </div>
  )
}
