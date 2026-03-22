// Project activity feed: chronological list of project events with relative timestamps

import { useState, useEffect } from 'react'
import { Activity, User, GitBranch, Settings, Users, Archive } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import type { ProjectActivity } from '../../types/api-types'

interface Props {
  projectId: string
}

// Map action strings to human-readable labels and icons
const ACTION_META: Record<string, { label: string; icon: typeof Activity; color: string }> = {
  'project.created':  { label: 'created this project',    icon: Activity,   color: 'text-green-400' },
  'project.updated':  { label: 'updated project settings', icon: Settings,  color: 'text-blue-400' },
  'project.archived': { label: 'archived this project',   icon: Archive,    color: 'text-zinc-400' },
  'member.added':     { label: 'added a team member',     icon: Users,      color: 'text-purple-400' },
  'member.removed':   { label: 'removed a team member',   icon: Users,      color: 'text-red-400' },
  'run.started':      { label: 'started a run',           icon: GitBranch,  color: 'text-yellow-400' },
  'run.completed':    { label: 'completed a run',         icon: GitBranch,  color: 'text-green-400' },
  'run.failed':       { label: 'run failed',              icon: GitBranch,  color: 'text-red-400' },
}

function getActionMeta(action: string) {
  return ACTION_META[action] ?? { label: action, icon: Activity, color: 'text-zinc-400' }
}

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime()
  const secs = Math.floor(diff / 1000)
  if (secs < 60) return 'just now'
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return new Date(isoString).toLocaleDateString()
}

function shortUserId(userId: string): string {
  // Show last 8 chars of UUID for brevity when no display name available
  return userId.length > 8 ? `…${userId.slice(-8)}` : userId
}

function parseDetails(detailsJson: string): Record<string, unknown> {
  try {
    return JSON.parse(detailsJson) as Record<string, unknown>
  } catch {
    return {}
  }
}

function ActivityRow({ activity }: { activity: ProjectActivity }) {
  const meta = getActionMeta(activity.action)
  const Icon = meta.icon
  const details = parseDetails(activity.details_json)

  // Build contextual suffix from details
  let suffix = ''
  if (details.target_user_id) suffix = ` (user ${shortUserId(String(details.target_user_id))})`
  else if (details.name) suffix = ` "${details.name}"`
  else if (details.role) suffix = ` as ${details.role}`

  return (
    <div className="flex items-start gap-3 py-3 border-b border-zinc-800/60 last:border-0">
      <div className={`mt-0.5 shrink-0 ${meta.color}`}>
        <Icon size={14} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-zinc-300 leading-snug">
          <span className="text-zinc-500 font-mono text-xs mr-1">
            <User size={10} className="inline mr-0.5 align-baseline" />
            {shortUserId(activity.user_id)}
          </span>
          {meta.label}
          {activity.module_id && (
            <span className="text-zinc-500 text-xs ml-1">
              on module <span className="text-zinc-400 font-mono">{activity.module_id.slice(-8)}</span>
            </span>
          )}
          <span className="text-zinc-600 text-xs">{suffix}</span>
        </p>
      </div>
      <time
        className="text-xs text-zinc-600 whitespace-nowrap shrink-0"
        title={new Date(activity.created_at).toLocaleString()}
      >
        {relativeTime(activity.created_at)}
      </time>
    </div>
  )
}

export function ActivityFeed({ projectId }: Props) {
  const [activities, setActivities] = useState<ProjectActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    apiClient
      .get<ProjectActivity[]>(`/api/projects/${projectId}/activities`)
      .then(data => { if (!cancelled) setActivities(data) })
      .catch(err => { if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load activities') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId])

  if (loading) {
    return (
      <div className="py-6 text-center text-zinc-600 text-sm">
        Loading activity...
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-4 text-red-400 text-sm">{error}</div>
    )
  }

  if (activities.length === 0) {
    return (
      <div className="py-6 text-center text-zinc-600 text-sm">
        No activity recorded yet.
      </div>
    )
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 divide-zinc-800">
      {activities.map(activity => (
        <ActivityRow key={activity.id} activity={activity} />
      ))}
    </div>
  )
}
