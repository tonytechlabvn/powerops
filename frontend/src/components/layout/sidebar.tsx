// Sidebar navigation for the main app shell

import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileCode2,
  BriefcaseBusiness,
  CheckSquare,
  Settings,
  Database,
  Shield,
  Users,
  LogOut,
  FolderKanban,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { setAccessToken } from '../../services/api-client'

const NAV_ITEMS = [
  { to: '/',            label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/projects',    label: 'Projects',    icon: FolderKanban },
  { to: '/templates',   label: 'Templates',   icon: FileCode2 },
  { to: '/jobs',        label: 'Jobs',         icon: BriefcaseBusiness },
  { to: '/approvals',   label: 'Approvals',   icon: CheckSquare },
  { to: '/state',       label: 'State',        icon: Database },
  { to: '/policies',    label: 'Policies',     icon: Shield },
  { to: '/config',      label: 'Config',       icon: Settings },
  { to: '/settings',    label: 'Settings',     icon: Users },
]

export function Sidebar() {
  const handleLogout = () => {
    setAccessToken(null)
    window.location.href = '/login'
  }

  return (
    <aside className="w-56 shrink-0 flex flex-col bg-zinc-900 border-r border-zinc-800 min-h-screen">
      {/* Logo / branding */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-zinc-800">
        <span className="text-blue-400 font-bold text-lg tracking-tight">PowerOps</span>
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

      {/* Logout + version */}
      <div className="px-2 pb-2">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-zinc-400 hover:text-red-400 hover:bg-zinc-800 transition-colors w-full"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
      <div className="px-4 py-3 text-xs text-zinc-600 border-t border-zinc-800">
        PowerOps v2.0
      </div>
    </aside>
  )
}
