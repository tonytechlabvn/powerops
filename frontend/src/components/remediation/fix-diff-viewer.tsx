// Unified diff viewer for a single file fix — green additions, red deletions.
// Renders diff_lines from the remediation API response.

interface FixDiffViewerProps {
  filePath: string
  diffLines: string[]
  description: string
}

export function FixDiffViewer({ filePath, diffLines, description }: FixDiffViewerProps) {
  if (diffLines.length === 0) {
    return (
      <div className="text-zinc-500 text-xs italic px-3 py-2">
        No diff available — view the fixed content in the panel below.
      </div>
    )
  }

  return (
    <div className="border border-zinc-700 rounded overflow-hidden">
      {/* File header bar */}
      <div className="flex items-center justify-between bg-zinc-800 px-3 py-1.5">
        <span className="text-zinc-300 text-xs font-mono">{filePath}</span>
        {description && (
          <span className="text-zinc-500 text-xs truncate max-w-xs">{description}</span>
        )}
      </div>

      {/* Diff lines */}
      <div className="overflow-x-auto font-mono text-xs leading-5 max-h-64 overflow-y-auto">
        {diffLines.map((line, i) => (
          <DiffLine key={i} line={line} />
        ))}
      </div>
    </div>
  )
}

function DiffLine({ line }: { line: string }) {
  // Unified diff color coding
  if (line.startsWith('+++') || line.startsWith('---')) {
    return (
      <div className="px-3 py-0 text-zinc-500 bg-zinc-900">{line}</div>
    )
  }
  if (line.startsWith('@@')) {
    return (
      <div className="px-3 py-0 text-blue-400 bg-blue-950/30">{line}</div>
    )
  }
  if (line.startsWith('+')) {
    return (
      <div className="px-3 py-0 text-green-300 bg-green-950/30 whitespace-pre">{line}</div>
    )
  }
  if (line.startsWith('-')) {
    return (
      <div className="px-3 py-0 text-red-300 bg-red-950/30 whitespace-pre">{line}</div>
    )
  }
  return (
    <div className="px-3 py-0 text-zinc-400 bg-zinc-950 whitespace-pre">{line}</div>
  )
}
