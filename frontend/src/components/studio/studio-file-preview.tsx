// Tabbed file preview for AI Studio — shows generated template files with edit support.
// Adapted from ModuleFilePreviewTabs for Jinja2 template packages.

import { useState } from 'react'
import type { StudioValidation } from '../../types/studio-types'

interface StudioFilePreviewProps {
  files: Record<string, string>
  validation?: StudioValidation | null
  editable?: boolean
  onFileChange?: (filename: string, content: string) => void
  onSave?: () => void
  onDeploy?: () => void
  providers?: string[]
  tags?: string[]
}

const FILE_ORDER = ['main.tf.j2', 'variables.json', 'metadata.json']

function sortedFiles(files: Record<string, string>): string[] {
  const ordered = FILE_ORDER.filter(f => f in files)
  const rest = Object.keys(files).filter(f => !FILE_ORDER.includes(f)).sort()
  return [...ordered, ...rest]
}

export function StudioFilePreview({
  files,
  validation,
  editable = false,
  onFileChange,
  onSave,
  onDeploy,
  providers = [],
  tags = [],
}: StudioFilePreviewProps) {
  const filenames = sortedFiles(files)
  const [activeTab, setActiveTab] = useState(filenames[0] ?? '')

  if (filenames.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-zinc-600 gap-3">
        <span className="text-5xl">&#9889;</span>
        <p className="text-sm">Generated template files will appear here.</p>
      </div>
    )
  }

  const hclErrors = validation?.hcl_errors ?? {}
  const jinja2Errors = validation?.jinja2_errors ?? []
  const activeContent = files[activeTab] ?? ''

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-col flex-1 border border-zinc-700 rounded-lg overflow-hidden bg-zinc-950">
        {/* Tab bar */}
        <div className="flex items-center gap-1 px-2 py-1.5 bg-zinc-900 border-b border-zinc-700 overflow-x-auto">
          {filenames.map(fname => {
            const hasErrors = (hclErrors[fname]?.length ?? 0) > 0
            return (
              <button
                key={fname}
                onClick={() => setActiveTab(fname)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono
                            whitespace-nowrap transition-colors
                            ${activeTab === fname
                              ? 'bg-zinc-800 text-zinc-100 border border-zinc-600'
                              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                            }`}
              >
                {fname}
                {hasErrors && (
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" title="Errors" />
                )}
              </button>
            )
          })}

          {/* Validation badge */}
          {validation && (
            <span className={`ml-auto px-2 py-0.5 rounded text-xs font-medium
              ${validation.valid ? 'bg-green-950 text-green-400' : 'bg-red-950 text-red-400'}`}>
              {validation.valid ? 'Valid' : 'Errors'}
            </span>
          )}
        </div>

        {/* Jinja2 errors */}
        {activeTab === 'main.tf.j2' && jinja2Errors.length > 0 && (
          <div className="bg-red-950/30 border-b border-red-800/50 px-3 py-2 space-y-0.5">
            {jinja2Errors.map((err, i) => (
              <p key={i} className="text-red-400 text-xs font-mono">Jinja2: {err}</p>
            ))}
          </div>
        )}

        {/* HCL errors for rendered output */}
        {hclErrors[activeTab]?.length > 0 && (
          <div className="bg-red-950/30 border-b border-red-800/50 px-3 py-2 space-y-0.5">
            {hclErrors[activeTab].map((err, i) => (
              <p key={i} className="text-red-400 text-xs font-mono">HCL: {err}</p>
            ))}
          </div>
        )}

        {/* File content */}
        <div className="flex-1 overflow-auto p-0">
          {editable && onFileChange ? (
            <textarea
              value={activeContent}
              onChange={e => onFileChange(activeTab, e.target.value)}
              spellCheck={false}
              className="w-full h-full min-h-[300px] bg-zinc-950 text-zinc-200 text-xs
                         font-mono p-4 resize-none focus:outline-none border-0"
            />
          ) : (
            <pre className="p-4 text-xs font-mono text-green-300 whitespace-pre-wrap overflow-auto">
              {activeContent || <span className="text-zinc-600 italic">Empty file</span>}
            </pre>
          )}
        </div>

        {/* Structure warnings */}
        {validation?.structure_warnings && validation.structure_warnings.length > 0 && (
          <div className="border-t border-zinc-800 bg-zinc-900 px-3 py-1.5">
            {validation.structure_warnings.map((w, i) => (
              <p key={i} className="text-yellow-400 text-xs">Warning: {w}</p>
            ))}
          </div>
        )}
      </div>

      {/* Bottom bar: metadata + save actions */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          {providers.length > 0 && (
            <span>Provider: <span className="text-zinc-300">{providers.join(', ')}</span></span>
          )}
          <span>Files: <span className="text-zinc-300">{filenames.length}</span></span>
          {tags.length > 0 && (
            <span>Tags: <span className="text-zinc-300">{tags.join(', ')}</span></span>
          )}
        </div>
        <div className="flex gap-2">
          {onSave && (
            <button
              onClick={onSave}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs
                         rounded font-medium transition-colors"
            >
              Save to Library
            </button>
          )}
          {onDeploy && (
            <button
              onClick={onDeploy}
              className="px-3 py-1.5 border border-zinc-600 text-zinc-300 text-xs
                         rounded hover:bg-zinc-800 transition-colors"
            >
              Deploy to Workspace
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
