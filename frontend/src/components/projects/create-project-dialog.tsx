// Create project dialog: form with name/description + optional YAML paste

import { useState } from 'react'
import { X } from 'lucide-react'
import { apiClient } from '../../services/api-client'

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function CreateProjectDialog({ onClose, onCreated }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [configYaml, setConfigYaml] = useState('')
  const [mode, setMode] = useState<'form' | 'yaml'>('form')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-100">New Project</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded px-3 py-2">
              {error}
            </div>
          )}

          {/* Mode toggle */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode('form')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                mode === 'form' ? 'bg-blue-500/20 text-blue-400' : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
              }`}
            >
              Form
            </button>
            <button
              type="button"
              onClick={() => setMode('yaml')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                mode === 'yaml' ? 'bg-blue-500/20 text-blue-400' : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
              }`}
            >
              YAML Config
            </button>
          </div>

          {/* Name */}
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

          {/* Description */}
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

          {/* YAML config (shown in yaml mode) */}
          {mode === 'yaml' && (
            <div>
              <label className="block text-sm text-zinc-400 mb-1">
                project.yaml <span className="text-zinc-600">(optional — auto-creates modules)</span>
              </label>
              <textarea
                value={configYaml}
                onChange={e => setConfigYaml(e.target.value)}
                rows={12}
                className="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm font-mono placeholder-zinc-600 focus:outline-none focus:border-blue-500 resize-y"
                placeholder={`name: hybrid-aws-proxmox
providers:
  - aws
  - proxmox
modules:
  - name: aws-networking
    path: modules/aws/networking
    provider: aws
  - name: aws-compute
    path: modules/aws/compute
    provider: aws
    depends_on: [aws-networking]
  - name: proxmox-database
    path: modules/proxmox/database
    provider: proxmox`}
              />
            </div>
          )}

          {/* Actions */}
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
      </div>
    </div>
  )
}
