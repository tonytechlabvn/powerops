// Create project dialog: three tabs — From Scratch, From Template, AI Wizard

import { useState } from 'react'
import { X } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import { TemplateBrowserPanel } from './template-browser-panel'
import { TemplatePreviewDialog } from './template-preview-dialog'
import { AiWizardPanel } from './ai-wizard-panel'

interface Props {
  onClose: () => void
  onCreated: () => void
}

type Tab = 'scratch' | 'template' | 'wizard'

export function CreateProjectDialog({ onClose, onCreated }: Props) {
  const [tab, setTab] = useState<Tab>('scratch')

  // From Scratch state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [configYaml, setConfigYaml] = useState('')
  const [scratchMode, setScratchMode] = useState<'form' | 'yaml'>('form')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // From Template state
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)

  async function handleScratchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await apiClient.post('/api/projects', {
        name: name.trim(),
        description: description.trim(),
        config_yaml: configYaml.trim(),
      })
      onCreated()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setSubmitting(false)
    }
  }

  const tabClass = (t: Tab) =>
    `px-3 py-1.5 text-xs font-medium rounded transition-colors ${
      tab === t
        ? 'bg-blue-500/20 text-blue-400'
        : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
    }`

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800 shrink-0">
            <h2 className="text-lg font-semibold text-zinc-100">New Project</h2>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
              <X size={18} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="p-5 space-y-4">
              {/* Tab switcher */}
              <div className="flex gap-2">
                <button type="button" className={tabClass('scratch')} onClick={() => setTab('scratch')}>
                  From Scratch
                </button>
                <button type="button" className={tabClass('template')} onClick={() => setTab('template')}>
                  From Template
                </button>
                <button type="button" className={tabClass('wizard')} onClick={() => setTab('wizard')}>
                  AI Wizard
                </button>
              </div>

              {/* Tab: From Scratch */}
              {tab === 'scratch' && (
                <form onSubmit={handleScratchSubmit} className="space-y-4">
                  {error && (
                    <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded px-3 py-2">
                      {error}
                    </div>
                  )}

                  {/* Sub-mode toggle */}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setScratchMode('form')}
                      className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                        scratchMode === 'form' ? 'bg-zinc-700 text-zinc-300' : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
                      }`}
                    >
                      Form
                    </button>
                    <button
                      type="button"
                      onClick={() => setScratchMode('yaml')}
                      className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                        scratchMode === 'yaml' ? 'bg-zinc-700 text-zinc-300' : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
                      }`}
                    >
                      YAML Config
                    </button>
                  </div>

                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Project Name</label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={e => setName(e.target.value)}
                      className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm placeholder-zinc-600 focus:outline-none focus:border-blue-500"
                      placeholder="hybrid-aws-proxmox"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Description</label>
                    <input
                      type="text"
                      value={description}
                      onChange={e => setDescription(e.target.value)}
                      className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm placeholder-zinc-600 focus:outline-none focus:border-blue-500"
                      placeholder="Hybrid cloud deployment with AWS and Proxmox"
                    />
                  </div>

                  {scratchMode === 'yaml' && (
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1">
                        project.yaml <span className="text-zinc-600">(optional — auto-creates modules)</span>
                      </label>
                      <textarea
                        value={configYaml}
                        onChange={e => setConfigYaml(e.target.value)}
                        rows={10}
                        className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm font-mono placeholder-zinc-600 focus:outline-none focus:border-blue-500 resize-y"
                        placeholder={`name: hybrid-aws-proxmox\nproviders:\n  - aws\n  - proxmox\nmodules:\n  - name: aws-networking\n    path: modules/aws/networking\n    provider: aws`}
                      />
                    </div>
                  )}

                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting || !name.trim()}
                      className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 disabled:cursor-not-allowed text-white font-medium rounded transition-colors"
                    >
                      {submitting ? 'Creating...' : 'Create Project'}
                    </button>
                  </div>
                </form>
              )}

              {/* Tab: From Template */}
              {tab === 'template' && (
                <TemplateBrowserPanel onSelect={name => setSelectedTemplate(name)} />
              )}

              {/* Tab: AI Wizard */}
              {tab === 'wizard' && (
                <AiWizardPanel onCreated={onCreated} />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Template preview dialog (rendered outside the main dialog so it stacks above) */}
      {selectedTemplate && (
        <TemplatePreviewDialog
          templateName={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          onCreated={onCreated}
        />
      )}
    </>
  )
}
