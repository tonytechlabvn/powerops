// Top header: search slot (Cmd+K stub), health indicator, theme toggle.
// Search is decorative for now — full command palette is P3 follow-up.

import { Search, Sun, Moon } from 'lucide-react'
import { useTheme } from '../../hooks/use-theme'
import { useHealth } from '../../hooks/use-api'
import { StatusDot } from '../_design-system/status-dot'
import { IconButton } from '../_design-system/icon-button'

export function Header() {
  const { theme, toggleTheme } = useTheme()
  const { data: health } = useHealth()

  const healthIntent =
    health?.status === 'healthy' ? 'success'
    : health?.status === 'degraded' ? 'warning'
    : 'danger'

  return (
    <header className="h-14 shrink-0 flex items-center gap-4 px-6 border-b border-zinc-800 bg-zinc-900">
      {/* Search slot — decorative until command palette arrives */}
      <div className="flex-1 max-w-xl">
        <button
          type="button"
          className="flex w-full items-center gap-2 h-9 px-3 rounded-md border border-zinc-800 bg-zinc-950/40 text-zinc-500 hover:text-zinc-300 hover:border-zinc-700 transition-colors duration-150 text-left"
        >
          <Search size={14} />
          <span className="text-xs">Search workspaces, jobs, modules…</span>
          <kbd className="ml-auto text-[10px] font-mono text-zinc-600 border border-zinc-800 rounded px-1.5 py-0.5">
            Ctrl K
          </kbd>
        </button>
      </div>

      {/* Health indicator */}
      {health && (
        <div className="hidden md:flex items-center gap-2 text-xs text-zinc-400">
          <StatusDot intent={healthIntent} />
          <span className="font-medium text-zinc-300">{health.status}</span>
          {health.terraform_version && (
            <span className="text-zinc-600 font-mono">tf {health.terraform_version}</span>
          )}
        </div>
      )}

      {/* Theme toggle */}
      <IconButton
        aria-label="Toggle dark mode"
        onClick={toggleTheme}
      >
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </IconButton>
    </header>
  )
}
