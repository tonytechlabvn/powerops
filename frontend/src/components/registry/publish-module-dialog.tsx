// Publish Module dialog — create new module or publish a new version

import { useState } from 'react'
import { X, Upload, AlertCircle } from 'lucide-react'
import { usePublishModule, usePublishVersion } from '../../hooks/use-module-registry'

interface Props {
  onClose: () => void
  /** If provided, pre-selects the module and only shows the version upload form */
  existingModuleId?: string
}

const SEMVER_RE = /^\d+\.\d+\.\d+$/

export function PublishModuleDialog({ onClose, existingModuleId }: Props) {
  // Module fields
  const [namespace, setNamespace] = useState('')
  const [name, setName] = useState('')
  const [provider, setProvider] = useState('aws')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState('')

  // Version fields
  const [version, setVersion] = useState('')
  const [archiveFile, setArchiveFile] = useState<File | null>(null)

  // State
  const [step, setStep] = useState<'module' | 'version'>(existingModuleId ? 'version' : 'module')
  const [createdModuleId, setCreatedModuleId] = useState(existingModuleId ?? '')
  const [error, setError] = useState('')

  const publishModule = usePublishModule()
  const publishVersion = usePublishVersion(createdModuleId)

  const versionError = version && !SEMVER_RE.test(version)
    ? 'Version must be in MAJOR.MINOR.PATCH format (e.g. 1.0.0)'
    : ''

  async function handlePublishModule() {
    setError('')
    if (!namespace.trim() || !name.trim() || !provider.trim()) {
      setError('Namespace, name, and provider are required')
      return
    }
    try {
      const mod = await publishModule.mutateAsync({
        namespace: namespace.trim().toLowerCase(),
        name: name.trim().toLowerCase(),
        provider: provider.trim().toLowerCase(),
        description,
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      })
      setCreatedModuleId(mod.id)
      setStep('version')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to publish module')
    }
  }

  async function handlePublishVersion() {
    setError('')
    if (!version || versionError) {
      setError('A valid semver version is required')
      return
    }
    if (!archiveFile) {
      setError('Please select a zip archive to upload')
      return
    }
    try {
      await publishVersion.mutateAsync({ version, file: archiveFile })
      onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to publish version')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h2 className="text-base font-semibold text-zinc-100">
            {step === 'module' ? 'Publish Module' : 'Publish Version'}
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-5 space-y-4">
          {step === 'module' && (
            <>
              <Field label="Namespace" required>
                <input
                  value={namespace}
                  onChange={e => setNamespace(e.target.value)}
                  placeholder="e.g. powerops"
                  className={inputCls}
                />
              </Field>
              <Field label="Module name" required>
                <input
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. aws-vpc"
                  className={inputCls}
                />
              </Field>
              <Field label="Provider" required>
                <select
                  value={provider}
                  onChange={e => setProvider(e.target.value)}
                  className={inputCls}
                >
                  <option value="aws">aws</option>
                  <option value="azurerm">azurerm</option>
                  <option value="google">google</option>
                  <option value="generic">generic</option>
                </select>
              </Field>
              <Field label="Description">
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  rows={2}
                  className={inputCls}
                  placeholder="Short description of what this module does"
                />
              </Field>
              <Field label="Tags (comma-separated)">
                <input
                  value={tags}
                  onChange={e => setTags(e.target.value)}
                  placeholder="networking, vpc, production"
                  className={inputCls}
                />
              </Field>
            </>
          )}

          {step === 'version' && (
            <>
              <Field label="Version" required hint="Semver: MAJOR.MINOR.PATCH">
                <input
                  value={version}
                  onChange={e => setVersion(e.target.value)}
                  placeholder="1.0.0"
                  className={inputCls}
                />
                {versionError && (
                  <p className="text-xs text-red-400 mt-1">{versionError}</p>
                )}
              </Field>
              <Field label="Module archive (.zip)" required>
                <label className="flex flex-col items-center gap-2 p-4 border-2 border-dashed border-zinc-700 rounded-md cursor-pointer hover:border-blue-500 transition-colors">
                  <Upload size={20} className="text-zinc-500" />
                  <span className="text-sm text-zinc-400">
                    {archiveFile ? archiveFile.name : 'Click to select zip archive'}
                  </span>
                  <input
                    type="file"
                    accept=".zip"
                    className="sr-only"
                    onChange={e => setArchiveFile(e.target.files?.[0] ?? null)}
                  />
                </label>
              </Field>
            </>
          )}

          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-md">
              <AlertCircle size={15} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-zinc-800">
          <button onClick={onClose} className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-200">
            Cancel
          </button>
          {step === 'module' && (
            <button
              onClick={handlePublishModule}
              disabled={publishModule.isPending}
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md disabled:opacity-50"
            >
              {publishModule.isPending ? 'Creating...' : 'Next: Add Version'}
            </button>
          )}
          {step === 'version' && (
            <button
              onClick={handlePublishVersion}
              disabled={publishVersion.isPending || !!versionError || !archiveFile}
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-md disabled:opacity-50"
            >
              {publishVersion.isPending ? 'Uploading...' : 'Publish Version'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const inputCls =
  'w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-md text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-blue-500'

function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string
  required?: boolean
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-zinc-400">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
        {hint && <span className="ml-1.5 text-zinc-600 font-normal">{hint}</span>}
      </label>
      {children}
    </div>
  )
}
