// Sidebar navigation for the main app shell

import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileCode2,
  BriefcaseBusiness,
  CheckSquare,
  Settings,
} from 'lucide-react'
import { cn } from '../../lib/utils'

const NAV_ITEMS = [
  { to: '/',            label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/templates',  label: 'Templates',  icon: FileCode2 },
  { to: '/jobs',       label: 'Jobs',        icon: BriefcaseBusiness },
  { to: '/approvals',  label: 'Approvals',  icon: CheckSquare },
  { to: '/config',     label: 'Config',      icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 flex flex-col bg-zinc-900 border-r border-zinc-800 min-h-screen">
      {/* Logo / branding */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-zinc-800">
        <span className="text-blue-400 font-bold text-lg tracking-tight">TerraBot</span>
      </div>

      {/* Nav links */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800',
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer version hint */}
      <div className="px-4 py-3 text-xs text-zinc-600 border-t border-zinc-800">
        TerraBot v1.0
      </div>
    </aside>
  )
}
