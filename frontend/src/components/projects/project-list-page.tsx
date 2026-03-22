// Project list page: card grid with status badges, search, and create button

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, FolderKanban, Users, Layers } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import type { ProjectSummary } from '../../types/api-types'
import { CreateProjectDialog } from './create-project-dialog'

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-yellow-500/20 text-yellow-400',
  active: 'bg-green-500/20 text-green-400',
  archived: 'bg-zinc-500/20 text-zinc-400',
}

export function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [search, setSearch] = useState('')

  async function fetchProjects() {
    try {
      const data = await apiClient.get<ProjectSummary[]>('/api/projects')
      setProjects(data)
    } catch (err) {
      console.error('Failed to load projects:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchProjects() }, [])

  const filtered = projects.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.description.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Projects</h1>
          <p className="text-zinc-500 text-sm mt-1">Multi-provider infrastructure projects</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          New Project
        </button>
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search projects..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="w-full max-w-sm bg-zinc-800 border border-zinc-700 text-zinc-100 rounded px-3 py-2 text-sm placeholder-zinc-500 focus:outline-none focus:border-blue-500 mb-6"
      />

      {/* Grid */}
      {loading ? (
        <div className="text-zinc-500 text-sm">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="text-zinc-500 text-sm">
          {projects.length === 0 ? 'No projects yet. Create your first project.' : 'No matching projects.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(project => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition-colors group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FolderKanban size={18} className="text-blue-400" />
                  <h3 className="text-zinc-100 font-medium group-hover:text-blue-400 transition-colors">
                    {project.name}
                  </h3>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[project.status] || STATUS_COLORS.draft}`}>
                  {project.status}
                </span>
              </div>

              <p className="text-zinc-500 text-sm mb-4 line-clamp-2">
                {project.description || 'No description'}
              </p>

              <div className="flex items-center gap-4 text-xs text-zinc-500">
                <span className="flex items-center gap-1">
                  <Layers size={12} />
                  {project.module_count} modules
                </span>
                <span className="flex items-center gap-1">
                  <Users size={12} />
                  {project.member_count} members
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create dialog */}
      {showCreate && (
        <CreateProjectDialog
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); fetchProjects() }}
        />
      )}
    </div>
  )
}
