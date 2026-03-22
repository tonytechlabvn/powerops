// Recursive tree node row for the file tree panel.
// Handles expand/collapse for directories and file selection.

import { useState } from 'react'
import { ChevronRight, ChevronDown, FileCode2, FolderOpen, Folder, MoreVertical } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface TreeNode {
  name: string
  path: string
  isDirectory: boolean
  children: TreeNode[]
}

interface TreeNodeRowProps {
  node: TreeNode
  depth: number
  selectedPath: string | null
  onSelectFile: (path: string) => void
  onContextMenu: (e: React.MouseEvent, node: TreeNode) => void
}

function fileIcon(name: string) {
  if (name.endsWith('.tf') || name.endsWith('.tfvars') || name.endsWith('.hcl')) {
    return <FileCode2 size={14} className="text-blue-400 shrink-0" />
  }
  return <FileCode2 size={14} className="text-zinc-400 shrink-0" />
}

export function TreeNodeRow({ node, depth, selectedPath, onSelectFile, onContextMenu }: TreeNodeRowProps) {
  const [expanded, setExpanded] = useState(true)
  const isSelected = selectedPath === node.path

  const handleClick = () => {
    if (node.isDirectory) {
      setExpanded(e => !e)
    } else {
      onSelectFile(node.path)
    }
  }

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer select-none text-sm group',
          isSelected ? 'bg-blue-600/20 text-blue-300' : 'text-zinc-300 hover:bg-zinc-800',
        )}
        style={{ paddingLeft: `${8 + depth * 12}px` }}
        onClick={handleClick}
        onContextMenu={e => onContextMenu(e, node)}
      >
        {node.isDirectory ? (
          <>
            <span className="shrink-0 text-zinc-500">
              {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </span>
            {expanded
              ? <FolderOpen size={14} className="text-yellow-400 shrink-0" />
              : <Folder size={14} className="text-yellow-400 shrink-0" />}
          </>
        ) : (
          <>
            <span className="w-3 shrink-0" />
            {fileIcon(node.name)}
          </>
        )}
        <span className="truncate">{node.name}</span>
        <button
          className="ml-auto opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-zinc-200 p-0.5 rounded"
          onClick={e => { e.stopPropagation(); onContextMenu(e, node) }}
        >
          <MoreVertical size={12} />
        </button>
      </div>

      {node.isDirectory && expanded && node.children.map(child => (
        <TreeNodeRow
          key={child.path}
          node={child}
          depth={depth + 1}
          selectedPath={selectedPath}
          onSelectFile={onSelectFile}
          onContextMenu={onContextMenu}
        />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Build flat FileInfo list into a tree structure
// ---------------------------------------------------------------------------

interface FlatFile {
  path: string
  is_directory: boolean
}

export function buildFileTree(files: FlatFile[]): TreeNode[] {
  const root: TreeNode[] = []
  const dirs = new Map<string, TreeNode>()

  const sorted = [...files].sort((a, b) => {
    if (a.is_directory !== b.is_directory) return a.is_directory ? -1 : 1
    return a.path.localeCompare(b.path)
  })

  for (const f of sorted) {
    const parts = f.path.split('/')
    let current = root
    let cumPath = ''

    for (let i = 0; i < parts.length - 1; i++) {
      cumPath = cumPath ? `${cumPath}/${parts[i]}` : parts[i]
      if (!dirs.has(cumPath)) {
        const node: TreeNode = { name: parts[i], path: cumPath, isDirectory: true, children: [] }
        dirs.set(cumPath, node)
        current.push(node)
      }
      current = dirs.get(cumPath)!.children
    }

    const leaf: TreeNode = {
      name: parts[parts.length - 1],
      path: f.path,
      isDirectory: f.is_directory,
      children: [],
    }
    if (f.is_directory) {
      if (!dirs.has(f.path)) { dirs.set(f.path, leaf); current.push(leaf) }
    } else {
      current.push(leaf)
    }
  }

  return root
}
