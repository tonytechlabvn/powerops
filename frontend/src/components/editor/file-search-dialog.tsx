// Full-text search dialog across workspace files.
// Triggered via Ctrl+Shift+F or the search button in the editor toolbar.

import { useState, useEffect, useRef } from 'react'
import { Search, X, FileCode2 } from 'lucide-react'
import type { SearchResult } from '../../types/api-types'

interface FileSearchDialogProps {
  isOpen: boolean
  onClose: () => void
  onSearch: (query: string) => Promise<SearchResult[]>
  onSelectResult: (path: string, line: number) => void
}

export function FileSearchDialog({ isOpen, onClose, onSearch, onSelectResult }: FileSearchDialogProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searched, setSearched] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input when dialog opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
      setResults([])
      setSearched(false)
    }
  }, [isOpen])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  const handleSearch = async () => {
    const q = query.trim()
    if (!q) return
    setIsSearching(true)
    try {
      const res = await onSearch(q)
      setResults(res)
      setSearched(true)
    } finally {
      setIsSearching(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  if (!isOpen) return null

  // Group results by file path
  const grouped = results.reduce<Record<string, SearchResult[]>>((acc, r) => {
    if (!acc[r.path]) acc[r.path] = []
    acc[r.path].push(r)
    return acc
  }, {})

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/60 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-2xl mx-4 flex flex-col max-h-[70vh]">
        {/* Search input row */}
        <div className="flex items-center gap-2 p-3 border-b border-zinc-800">
          <Search size={15} className="text-zinc-500 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search across workspace files..."
            className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-600 text-sm outline-none"
          />
          {isSearching && (
            <span className="text-xs text-zinc-500 animate-pulse">Searching...</span>
          )}
          <button
            onClick={handleSearch}
            disabled={isSearching || !query.trim()}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded transition-colors"
          >
            Search
          </button>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 p-1 rounded">
            <X size={15} />
          </button>
        </div>

        {/* Results */}
        <div className="overflow-y-auto flex-1">
          {searched && results.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-zinc-600">
              No matches found for "{query}"
            </div>
          )}

          {Object.entries(grouped).map(([filePath, fileResults]) => (
            <div key={filePath}>
              {/* File header */}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800/50 border-b border-zinc-800 sticky top-0">
                <FileCode2 size={12} className="text-blue-400 shrink-0" />
                <span className="text-xs font-mono text-zinc-300">{filePath}</span>
                <span className="ml-auto text-xs text-zinc-600">{fileResults.length} match{fileResults.length !== 1 ? 'es' : ''}</span>
              </div>

              {/* Match rows */}
              {fileResults.map((r, i) => (
                <button
                  key={i}
                  className="w-full text-left px-3 py-2 border-b border-zinc-800/50 hover:bg-zinc-800 transition-colors"
                  onClick={() => { onSelectResult(r.path, r.line); onClose() }}
                >
                  <div className="flex items-baseline gap-3">
                    <span className="text-xs text-zinc-600 shrink-0 font-mono w-8 text-right">{r.line}</span>
                    <span className="text-xs font-mono text-zinc-300 truncate">{r.content.trim()}</span>
                  </div>
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* Footer */}
        {results.length > 0 && (
          <div className="px-3 py-1.5 border-t border-zinc-800 text-xs text-zinc-600">
            {results.length} result{results.length !== 1 ? 's' : ''} in {Object.keys(grouped).length} file{Object.keys(grouped).length !== 1 ? 's' : ''}
          </div>
        )}
      </div>
    </div>
  )
}
