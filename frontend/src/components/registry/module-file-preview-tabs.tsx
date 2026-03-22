// Tabbed view of generated Terraform module files — Monaco read/edit mode per tab.

import { useState } from 'react'
import type { ModuleValidationResponse } from '../../types/api-types'

interface ModuleFilePreviewTabsProps {
  files: Record<string, string>
  validation?: ModuleValidationResponse | null
  editable?: boolean
  onFileChange?: (filename: string, content: string) => void
}

const FILE_ORDER = ['main.tf', 'variables.tf', 'outputs.tf', 'README.md', 'versions.tf']

function sortedFiles(files: Record<string, string>): string[] {
  const ordered = FILE_ORDER.filter(f => f in files)
  const rest = Object.keys(files).filter(f => !FILE_ORDER.includes(f)).sort()
  return [...ordered, ...rest]
}

export function ModuleFilePreviewTabs({
  files,
  validation,
  editable = false,
  onFileChange,
}: ModuleFilePreviewTabsProps) {
  const filenames = sortedFiles(files)
  const [activeTab, setActiveTab] = useState(filenames[0] ?? '')

  if (filenames.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-zinc-500 text-sm">
        No files generated yet.
      </div>
    )
  }

  const fileErrors = validation?.file_errors ?? {}
  const activeContent = files[activeTab] ?? ''
  const isMarkdown = activeTab.endsWith('.md')

  return (
    <div className="flex flex-col h-full border border-zinc-700 rounded-lg overflow-hidden bg-zinc-950">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-2 py-1.5 bg-zinc-900 border-b border-zinc-700 overflow-x-auto">
        {filenames.map(fname => {
          const hasErrors = (fileErrors[fname]?.length ?? 0) > 0
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
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" title="Validation errors" />
              )}
            </button>
          )
        })}
      </div>

      {/* Validation errors for active tab */}
      {fileErrors[activeTab]?.length > 0 && (
        <div className="bg-red-950/30 border-b border-red-800/50 px-3 py-2 space-y-0.5">
          {fileErrors[activeTab].map((err, i) => (
            <p key={i} className="text-red-400 text-xs font-mono">✕ {err}</p>
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
          <pre className={`p-4 text-xs font-mono whitespace-pre-wrap overflow-auto
                          ${isMarkdown ? 'text-zinc-300' : 'text-green-300'}`}>
            {activeContent || <span className="text-zinc-600 italic">Empty file</span>}
          </pre>
        )}
      </div>

      {/* Structure warnings footer */}
      {validation?.structure_warnings && validation.structure_warnings.length > 0 && (
        <div className="border-t border-zinc-800 bg-zinc-900 px-3 py-1.5">
          {validation.structure_warnings.map((w, i) => (
            <p key={i} className="text-yellow-400 text-xs">⚠ {w}</p>
          ))}
        </div>
      )}
    </div>
  )
}
