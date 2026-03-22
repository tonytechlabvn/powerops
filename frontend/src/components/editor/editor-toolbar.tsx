// Toolbar for the HCL editor page: filename display, search, refresh, save.

import { Search, Save, RefreshCw } from 'lucide-react'

interface EditorToolbarProps {
  selectedPath: string | null
  hasUnsavedChanges: boolean
  isSaving: boolean
  isLoading: boolean
  onSave: () => void
  onSearch: () => void
  onRefresh: () => void
}

export function EditorToolbar({
  selectedPath,
  hasUnsavedChanges,
  isSaving,
  isLoading,
  onSave,
  onSearch,
  onRefresh,
}: EditorToolbarProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800 bg-zinc-900 shrink-0">
      {/* Current file path */}
      <span className="text-sm text-zinc-400 truncate flex-1">
        {selectedPath
          ? <span className="font-mono text-zinc-200">{selectedPath}</span>
          : <span className="italic">Select a file from the tree</span>
        }
      </span>

      <button
        title="Search (Ctrl+Shift+F)"
        className="p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 rounded"
        onClick={onSearch}
      >
        <Search size={15} />
      </button>

      <button
        title="Refresh file tree"
        className="p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 rounded"
        onClick={onRefresh}
      >
        <RefreshCw size={15} className={isLoading ? 'animate-spin' : ''} />
      </button>

      <button
        title="Save (Ctrl+S)"
        disabled={!selectedPath || !hasUnsavedChanges || isSaving}
        className="flex items-center gap-1.5 px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded transition-colors"
        onClick={onSave}
      >
        <Save size={13} />
        {isSaving ? 'Saving…' : 'Save'}
      </button>
    </div>
  )
}
