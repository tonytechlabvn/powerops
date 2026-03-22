// Project detail page: tabs for modules, team, runs with status overview

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Layers, Users, Play, GitBranch } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import type { ProjectDetail } from '../../types/api-types'

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-yellow-500/20 text-yellow-400',
  active: 'bg-green-500/20 text-green-400',
  archived: 'bg-zinc-500/20 text-zinc-400',
  pending: 'bg-zinc-500/20 text-zinc-400',
  planning: 'bg-blue-500/20 text-blue-400',
  applying: 'bg-yellow-500/20 text-yellow-400',
  applied: 'bg-green-500/20 text-green-400',
  failed: 'bg-red-500/20 text-red-400',
  running: 'bg-yellow-500/20 text-yellow-400',
  completed: 'bg-green-500/20 text-green-400',
}

type Tab = 'modules' | 'team' | 'runs'

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('modules')

  useEffect(() => {
    if (!id) return
    apiClient.get<ProjectDetail>(`/api/projects/${id}`)
      .then(setProject)
      .catch(() => navigate('/projects'))
      .finally(() => setLoading(false))
  }, [id, navigate])

  if (loading) return <div className="p-6 text-zinc-500">Loading...</div>
  if (!project) return null

  const tabs: { key: Tab; label: string; icon: typeof Layers; count: number }[] = [
    { key: 'modules', label: 'Modules', icon: Layers, count: project.modules.length },
    { key: 'team', label: 'Team', icon: Users, count: project.members.length },
    { key: 'runs', label: 'Runs', icon: Play, count: project.runs.length },
  ]

  return (
    <div className="p-6">
      {/* Back + header */}
      <button
        onClick={() => navigate('/projects')}
        className="flex items-center gap-1 text-zinc-500 hover:text-zinc-300 text-sm mb-4 transition-colors"
      >
        <ArrowLeft size={14} />
        Back to Projects
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">{project.name}</h1>
          <p className="text-zinc-500 text-sm mt-1">{project.description || 'No description'}</p>
        </div>
        <span className={`text-xs px-3 py-1 rounded-full font-medium ${STATUS_COLORS[project.status]}`}>
          {project.status}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-800 mb-6">
        {tabs.map(({ key, label, icon: Icon, count }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <Icon size={14} />
            {label}
            <span className="text-xs bg-zinc-800 px-1.5 py-0.5 rounded">{count}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'modules' && <ModulesTab project={project} />}
      {tab === 'team' && <TeamTab project={project} />}
      {tab === 'runs' && <RunsTab project={project} />}
    </div>
  )
}

function ModulesTab({ project }: { project: ProjectDetail }) {
  if (project.modules.length === 0) {
    return <div className="text-zinc-500 text-sm">No modules defined. Add a project.yaml config to create modules.</div>
  }

  return (
    <div className="space-y-3">
      {project.modules.map(mod => (
        <div key={mod.id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <GitBranch size={14} className="text-blue-400" />
              <span className="text-zinc-100 font-medium">{mod.name}</span>
              <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">{mod.provider}</span>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[mod.status] || STATUS_COLORS.pending}`}>
              {mod.status}
            </span>
          </div>
          <div className="text-xs text-zinc-500">
            <span>Path: {mod.path}</span>
            {mod.depends_on.length > 0 && (
              <span className="ml-4">Depends on: {mod.depends_on.join(', ')}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function TeamTab({ project }: { project: ProjectDetail }) {
  if (project.members.length === 0) {
    return <div className="text-zinc-500 text-sm">No team members yet.</div>
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-500">
            <th className="text-left px-4 py-3 font-medium">Member</th>
            <th className="text-left px-4 py-3 font-medium">Role</th>
            <th className="text-left px-4 py-3 font-medium">Modules</th>
          </tr>
        </thead>
        <tbody>
          {project.members.map(member => (
            <tr key={member.user_id} className="border-b border-zinc-800/50 last:border-0">
              <td className="px-4 py-3">
                <div className="text-zinc-100">{member.user_name || member.user_email}</div>
                <div className="text-xs text-zinc-500">{member.user_email}</div>
              </td>
              <td className="px-4 py-3">
                <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full">
                  {member.role_name}
                </span>
              </td>
              <td className="px-4 py-3 text-zinc-500 text-xs">
                {member.assigned_modules.length > 0 ? member.assigned_modules.join(', ') : 'All modules'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RunsTab({ project }: { project: ProjectDetail }) {
  if (project.runs.length === 0) {
    return <div className="text-zinc-500 text-sm">No runs yet.</div>
  }

  return (
    <div className="space-y-2">
      {project.runs.map(run => (
        <div key={run.id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[run.status] || STATUS_COLORS.pending}`}>
              {run.status}
            </span>
            <span className="text-zinc-100 text-sm">{run.run_type}</span>
            <span className="text-zinc-500 text-xs">on {run.module_name}</span>
          </div>
          <span className="text-zinc-500 text-xs">
            {new Date(run.started_at).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}
