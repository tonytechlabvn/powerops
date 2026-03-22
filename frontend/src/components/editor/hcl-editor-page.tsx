// Full-page HCL editor: file tree sidebar + Monaco editor + validation panel.
// Route: /workspaces/:id/editor
// Sub-components: FileTreePanel, EditorToolbar, MonacoHclEditor, ValidationPanel, FileSearchDialog

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useWorkspaceFiles } from '../../hooks/use-workspace-files'
import { FileTreePanel } from './file-tree-panel'
import { EditorToolbar } from './editor-toolbar'
import { MonacoHclEditor } from './monaco-hcl-editor'
import { ValidationPanel } from './validation-panel'
import { FileSearchDialog } from './file-search-dialog'

interface ValidationError {
  line?: number
  message: string
  severity?: 'error' | 'warning'
}

export function HCLEditorPage() {
  const { id: workspaceId = '' } = useParams<{ id: string }>()
  const fm = useWorkspaceFiles(workspaceId)

  const [editorContent, setEditorContent]       = useState('')
  const [savedChecksum, setSavedChecksum]         = useState<string | undefined>()
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [selectedPath, setSelectedPath]           = useState<string | null>(null)
  const [validationErrors, setValidationErrors]   = useState<ValidationError[]>([])
  const [isValid, setIsValid]                     = useState<boolean | null>(null)
  const [isSaving, setIsSaving]                   = useState(false)
  const [searchOpen, setSearchOpen]               = useState(false)

  // Load file tree on mount
  useEffect(() => {
    if (workspaceId) fm.listFiles('**/*')
  }, [workspaceId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Sync editor when file opened
  useEffect(() => {
    if (fm.openFile) {
      setEditorContent(fm.openFile.content)
      setSavedChecksum(fm.openFile.checksum)
      setHasUnsavedChanges(false)
      setValidationErrors([])
      setIsValid(null)
    }
  }, [fm.openFile])

  // Ctrl+Shift+F — open search dialog
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleSelectFile = useCallback(async (path: string) => {
    if (hasUnsavedChanges && !window.confirm('Discard unsaved changes and open another file?')) return
    setSelectedPath(path)
    await fm.readFile(path)
  }, [fm, hasUnsavedChanges])

  const handleEditorChange = useCallback((value: string) => {
    setEditorContent(value)
    setHasUnsavedChanges(value !== (fm.openFile?.content ?? ''))
  }, [fm.openFile])

  const handleSave = useCallback(async (content: string) => {
    if (!selectedPath) return
    setIsSaving(true)
    try {
      const result = await fm.updateFile(selectedPath, content, savedChecksum)
      setSavedChecksum(result.checksum)
      setHasUnsavedChanges(false)
      if (result.validation) {
        setIsValid(result.validation.valid)
        setValidationErrors(
          (result.validation.errors ?? []).map(msg => ({ message: msg, severity: 'error' as const }))
        )
      } else {
        setIsValid(null); setValidationErrors([])
      }
      await fm.listFiles('**/*')
    } catch (err) {
      alert(`Save failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsSaving(false)
    }
  }, [selectedPath, savedChecksum, fm])

  const handleCreateFile = useCallback(async (dirPath: string) => {
    const name = window.prompt('New file name (e.g. main.tf):')
    if (!name) return
    const fullPath = dirPath ? `${dirPath}/${name}` : name
    await fm.createFile(fullPath, '')
    await fm.listFiles('**/*')
    await handleSelectFile(fullPath)
  }, [fm, handleSelectFile])

  const handleCreateDirectory = useCallback(async (dirPath: string) => {
    const name = window.prompt('New folder name:')
    if (!name) return
    await fm.createDirectory(dirPath ? `${dirPath}/${name}` : name)
    await fm.listFiles('**/*')
  }, [fm])

  const handleRenameFile = useCallback(async (path: string) => {
    const parts = path.split('/')
    const newName = window.prompt('New name:', parts[parts.length - 1])
    if (!newName || newName === parts[parts.length - 1]) return
    const newPath = [...parts.slice(0, -1), newName].join('/')
    await fm.renameFile(path, newPath)
    await fm.listFiles('**/*')
    if (selectedPath === path) { setSelectedPath(newPath); await fm.readFile(newPath) }
  }, [fm, selectedPath])

  const handleDeleteFile = useCallback(async (path: string, isDir: boolean) => {
    if (!window.confirm(`Delete ${isDir ? 'directory' : 'file'} "${path}"?`)) return
    if (isDir) await fm.deleteDirectory(path)
    else await fm.deleteFile(path)
    await fm.listFiles('**/*')
    if (selectedPath === path) { setSelectedPath(null); fm.clearOpenFile() }
  }, [fm, selectedPath])

  return (
    <div className="flex h-full overflow-hidden bg-zinc-950">
      <FileTreePanel
        files={fm.files}
        selectedPath={selectedPath}
        onSelectFile={handleSelectFile}
        onCreateFile={handleCreateFile}
        onCreateDirectory={handleCreateDirectory}
        onRenameFile={handleRenameFile}
        onDeleteFile={handleDeleteFile}
      />

      <div className="flex flex-col flex-1 overflow-hidden">
        <EditorToolbar
          selectedPath={selectedPath}
          hasUnsavedChanges={hasUnsavedChanges}
          isSaving={isSaving}
          isLoading={fm.isLoading}
          onSave={() => handleSave(editorContent)}
          onSearch={() => setSearchOpen(true)}
          onRefresh={() => fm.listFiles('**/*')}
        />

        <div className="flex-1 overflow-hidden">
          {selectedPath ? (
            <MonacoHclEditor
              content={editorContent}
              language={fm.openFile?.language ?? 'hcl'}
              onChange={handleEditorChange}
              onSave={handleSave}
              validationErrors={validationErrors}
              hasUnsavedChanges={hasUnsavedChanges}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-zinc-600 gap-2">
              <span className="text-4xl">📄</span>
              <span className="text-sm">Select a file from the tree to start editing</span>
            </div>
          )}
        </div>

        <ValidationPanel errors={validationErrors} isValid={isValid} />
      </div>

      <FileSearchDialog
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSearch={query => fm.searchFiles(query)}
        onSelectResult={async (path) => { await handleSelectFile(path) }}
      />
    </div>
  )
}
