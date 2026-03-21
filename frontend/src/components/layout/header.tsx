// Top header bar with page title and dark mode toggle

import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../hooks/use-theme'
import { useHealth } from '../../hooks/use-api'

export function Header() {
  const { theme, toggleTheme } = useTheme()
  const { data: health } = useHealth()

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-zinc-800 bg-zinc-900 shrink-0">
      {/* Health indicator */}
      <div className="flex items-center gap-2">
        {health && (
          <span className="flex items-center gap-1.5 text-xs text-zinc-400">
            <span
              className={[
                'w-2 h-2 rounded-full',
                health.status === 'healthy'   ? 'bg-green-400' :
                health.status === 'degraded'  ? 'bg-yellow-400' :
                                                'bg-red-400',
              ].join(' ')}
            />
            {health.status}
            {health.terraform_version && (
              <span className="ml-2 text-zinc-600">tf {health.terraform_version}</span>
            )}
          </span>
        )}
      </div>

      {/* Dark mode toggle */}
      <button
        onClick={toggleTheme}
        aria-label="Toggle dark mode"
        className="p-2 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
      >
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </header>
  )
}
