// Sidebar with 5 grouped sections: Operate / Build / Library / Learn / Admin.
// Locked decision per plans/260508-2120-powerops-ui-full-redesign/plan.md.

import { NavLink, Link } from 'react-router-dom'
import {
  LayoutDashboard,
  FileCode2,
  BriefcaseBusiness,
  CheckSquare,
  Settings,
  Database,
  Shield,
  LogOut,
  FolderKanban,
  Layers,
  Variable,
  Package,
  Boxes,
  Bot,
  GraduationCap,
  GitBranch,
  Plus,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '../_design-system/lib/cn'
import { setAccessToken } from '../../services/api-client'

interface NavItem { to: string; label: string; icon: LucideIcon }
interface NavGroup { label: string; items: NavItem[] }

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Operate',
    items: [
      { to: '/',           label: 'Dashboard',  icon: LayoutDashboard },
      { to: '/jobs',       label: 'Jobs',       icon: BriefcaseBusiness },
      { to: '/approvals',  label: 'Approvals',  icon: CheckSquare },
      { to: '/state',      label: 'State',      icon: Database },
    ],
  },
  {
    label: 'Build',
    items: [
      { to: '/projects',     label: 'Projects',     icon: FolderKanban },
      { to: '/environments', label: 'Environments', icon: Layers },
      { to: '/stacks',       label: 'Stacks',       icon: Boxes },
      { to: '/studio',       label: 'AI Studio',    icon: Bot },
    ],
  },
  {
    label: 'Library',
    items: [
      { to: '/templates',     label: 'Templates', icon: FileCode2 },
      { to: '/registry',      label: 'Registry',  icon: Package },
      { to: '/variable-sets', label: 'Variables', icon: Variable },
    ],
  },
  {
    label: 'Learn',
    items: [
      { to: '/kb', label: 'Knowledge Base', icon: GraduationCap },
    ],
  },
  {
    label: 'Admin',
    items: [
      { to: '/policies', label: 'Policies', icon: Shield },
      { to: '/config',   label: 'Providers', icon: GitBranch },
      { to: '/settings', label: 'Settings',  icon: Settings },
    ],
  },
]

export function Sidebar() {
  const handleLogout = () => {
    setAccessToken(null)
    window.location.href = '/login'
  }

  return (
    <aside className="w-64 shrink-0 flex flex-col bg-zinc-900 border-r border-zinc-800 min-h-screen">
      {/* Branding */}
      <div className="flex items-center gap-2 px-4 h-14 border-b border-zinc-800 shrink-0">
        <div className="h-6 w-6 rounded bg-blue-500 flex items-center justify-center text-white text-xs font-bold">P</div>
        <span className="text-zinc-100 font-semibold text-sm tracking-tight">PowerOps</span>
      </div>

      {/* Primary CTA */}
      <div className="px-3 pt-3 shrink-0">
        <Link
          to="/projects"
          className="w-full inline-flex items-center justify-center gap-2 h-9 px-4 rounded-md bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-colors duration-150 shadow-sm shadow-blue-500/10"
        >
          <Plus size={16} />
          New Project
        </Link>
      </div>

      {/* Grouped nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="px-2 mb-1.5 text-xs font-medium uppercase tracking-wide text-zinc-500">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-2 py-1.5 rounded-md text-sm transition-colors duration-150',
                      isActive
                        ? 'bg-zinc-800 text-zinc-100'
                        : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60',
                    )
                  }
                >
                  <Icon size={16} className="shrink-0" />
                  <span className="truncate">{label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-zinc-800 shrink-0">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 px-2 py-1.5 rounded-md text-sm text-zinc-400 hover:text-red-400 hover:bg-zinc-800/60 transition-colors duration-150"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
      <div className="px-4 py-2 text-[10px] uppercase tracking-wider text-zinc-600 border-t border-zinc-800">
        PowerOps v2.0
      </div>
    </aside>
  )
}
