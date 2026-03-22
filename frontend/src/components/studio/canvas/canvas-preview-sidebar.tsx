// Canvas preview sidebar — local preview computed from graph state (zero API cost).
// Shows resource count, expected variables, connection warnings, and generate button.

import { useCanvasStore } from '../../../stores/canvas-store'

interface CanvasPreviewSidebarProps {
  onGenerate: () => void
  isGenerating: boolean
}

export function CanvasPreviewSidebar({ onGenerate, isGenerating }: CanvasPreviewSidebarProps) {
  const preview = useCanvasStore(s => s.getPreview())
  const nodeCount = useCanvasStore(s => s.nodes.length)
  const edgeCount = useCanvasStore(s => s.edges.length)

  const hasResources = Object.keys(preview.resourceCount).length > 0

  return (
    <div className="w-56 shrink-0 border-l border-zinc-800 bg-zinc-900 overflow-y-auto p-3 space-y-4">
      <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Preview</h3>

      {/* Resource counts */}
      <div>
        <h4 className="text-[10px] font-bold text-zinc-500 uppercase mb-1">Resources</h4>
        {hasResources ? (
          <div className="space-y-0.5">
            {Object.entries(preview.resourceCount).map(([type, count]) => (
              <div key={type} className="flex justify-between text-xs">
                <span className="text-zinc-400">{type.replace(/([A-Z])/g, ' $1').trim()}</span>
                <span className="text-zinc-200 font-mono">{count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-zinc-600 text-xs italic">Drag resources onto canvas</p>
        )}
      </div>

      {/* Stats */}
      <div className="flex gap-3 text-xs text-zinc-500">
        <span>Nodes: <span className="text-zinc-300">{nodeCount}</span></span>
        <span>Edges: <span className="text-zinc-300">{edgeCount}</span></span>
      </div>

      {/* Expected variables */}
      {preview.expectedVariables.length > 0 && (
        <div>
          <h4 className="text-[10px] font-bold text-zinc-500 uppercase mb-1">Expected Variables</h4>
          <div className="space-y-0.5">
            {preview.expectedVariables.map(v => (
              <p key={v} className="text-xs text-zinc-400 font-mono">{v}</p>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {preview.warnings.length > 0 && (
        <div>
          <h4 className="text-[10px] font-bold text-yellow-500 uppercase mb-1">Warnings</h4>
          {preview.warnings.map((w, i) => (
            <p key={i} className="text-xs text-yellow-400">{w}</p>
          ))}
        </div>
      )}

      {/* Generate button */}
      {hasResources && (
        <button
          onClick={onGenerate}
          disabled={isGenerating}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                     text-white text-xs rounded font-medium transition-colors"
        >
          {isGenerating ? 'Generating...' : 'Generate Template'}
        </button>
      )}
    </div>
  )
}
