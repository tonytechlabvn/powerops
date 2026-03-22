// Collapsible file tree sidebar panel for the HCL workspace editor.
// Tree node rendering and data building live in file-tree-node.tsx.

import { useState, useCallback } from 'react'
import { FilePlus, FolderPlus, Pencil, Trash2 } from 'lucide-react'
import { TreeNodeRow, buildFileTree, type TreeNode } from './file-tree-node'
import type { FileInfo } from '../../types/api-types'

interface FileTreePanelProps {
  files: FileInfo[]
  selectedPath: string | null
  onSelectFile: (path: string) => void
  onCreateFile: (dirPath: string) => void
  onCreateDirectory: (dirPath: string) => void
  onRenameFile: (path: string) => void
  onDeleteFile: (path: string, isDir: boolean) => void
}

interface ContextMenuState {
  x: number
  y: number
  node: TreeNode
}

export function FileTreePanel({
  files, selectedPath, onSelectFile,
  onCreateFile, onCreateDirectory, onRenameFile, onDeleteFile,
}: FileTreePanelProps) {
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)
  const tree = buildFileTree(files)

  const handleContextMenu = useCallback((e: React.MouseEvent, node: TreeNode) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY, node })
  }, [])

  const closeMenu = () => setContextMenu(null)

  return (
    <div
      className="h-full flex flex-col bg-zinc-900 border-r border-zinc-800 w-56 shrink-0 overflow-hidden"
      onClick={closeMenu}
    >
      {/* Panel header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Files</span>
        <div className="flex gap-1">
          <button title="New File" className="text-zinc-500 hover:text-zinc-200 p-0.5 rounded"
            onClick={() => onCreateFile('')}>
            <FilePlus size={14} />
          </button>
          <button title="New Folder" className="text-zinc-500 hover:text-zinc-200 p-0.5 rounded"
            onClick={() => onCreateDirectory('')}>
            <FolderPlus size={14} />
          </button>
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1">
        {tree.length === 0 ? (
          <div className="px-3 py-4 text-xs text-zinc-600 text-center">
            No files yet.<br />Create a .tf file to get started.
          </div>
        ) : (
          tree.map(node => (
            <TreeNodeRow
              key={node.path}
              node={node}
              depth={0}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
              onContextMenu={handleContextMenu}
            />
          ))
        )}
      </div>

      {/* Context menu */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-zinc-800 border border-zinc-700 rounded shadow-xl py-1 text-sm min-w-36"
          style={{ top: contextMenu.y, left: contextMenu.x }}
          onClick={e => e.stopPropagation()}
        >
          {contextMenu.node.isDirectory && (
            <>
              <button className="flex items-center gap-2 w-full px-3 py-1.5 text-zinc-300 hover:bg-zinc-700"
                onClick={() => { onCreateFile(contextMenu.node.path); closeMenu() }}>
                <FilePlus size={13} /> New File
              </button>
              <button className="flex items-center gap-2 w-full px-3 py-1.5 text-zinc-300 hover:bg-zinc-700"
                onClick={() => { onCreateDirectory(contextMenu.node.path); closeMenu() }}>
                <FolderPlus size={13} /> New Folder
              </button>
              <div className="border-t border-zinc-700 my-1" />
            </>
          )}
          <button className="flex items-center gap-2 w-full px-3 py-1.5 text-zinc-300 hover:bg-zinc-700"
            onClick={() => { onRenameFile(contextMenu.node.path); closeMenu() }}>
            <Pencil size={13} /> Rename
          </button>
          <button className="flex items-center gap-2 w-full px-3 py-1.5 text-red-400 hover:bg-zinc-700"
            onClick={() => { onDeleteFile(contextMenu.node.path, contextMenu.node.isDirectory); closeMenu() }}>
            <Trash2 size={13} /> Delete
          </button>
        </div>
      )}
    </div>
  )
}
