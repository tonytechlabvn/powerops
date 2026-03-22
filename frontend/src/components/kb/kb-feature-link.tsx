// Deep integration link — connects KB chapters to PowerOps features

import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'

const FEATURE_ROUTES: Record<string, { route: string; label: string }> = {
  'workspace-editor': { route: '/workspaces', label: 'Open Workspace Editor' },
  'plan-viewer': { route: '/jobs', label: 'See a Real Plan' },
  'variable-sets': { route: '/variable-sets', label: 'Manage Variables' },
  'module-registry': { route: '/registry', label: 'Browse Modules' },
  'ai-module-generator': { route: '/modules/generate', label: 'Generate a Module' },
  'stack-composer': { route: '/stacks', label: 'Build a Stack' },
  'vcs-workflow': { route: '/environments', label: 'Configure VCS' },
  'policy-editor': { route: '/policies', label: 'Write a Policy' },
}

interface Props {
  features: string[]
}

export function KBFeatureLinks({ features }: Props) {
  const links = features
    .map((f) => ({ key: f, ...FEATURE_ROUTES[f] }))
    .filter((l) => l.route)

  if (!links.length) return null

  return (
    <div className="rounded-lg border border-blue-600/30 bg-blue-600/5 p-4 space-y-3">
      <h3 className="text-sm font-medium text-blue-400">Try it in PowerOps</h3>
      <div className="flex flex-wrap gap-2">
        {links.map(({ key, route, label }) => (
          <Link
            key={key}
            to={route}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 transition-colors border border-blue-600/30"
          >
            {label}
            <ArrowRight size={14} />
          </Link>
        ))}
      </div>
    </div>
  )
}
