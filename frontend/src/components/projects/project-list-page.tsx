// Project list page: card grid with status badges, search, and create button

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, FolderKanban, Users, Layers } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import type { ProjectSummary } from '../../types/api-types'
import { CreateProjectDialog } from './create-project-dialog'
import { Button } from '../_design-system/button'
import { Badge, type BadgeProps } from '../_design-system/badge'
import { Input } from '../_design-system/input'
import { EmptyState } from '../_design-system/empty-state'
import { Skeleton } from '../_design-system/skeleton'

const STATUS_INTENT: Record<string, NonNullable<BadgeProps['intent']>> = {
  draft: 'warning',
  active: 'success',
  archived: 'neutral',
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Projects</h1>
          <p className="text-zinc-400 text-sm mt-1">Multi-provider infrastructure projects</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={16} />
          New Project
        </Button>
      </div>

      {/* Search */}
      <div className="max-w-sm">
        <Input
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2].map(i => <Skeleton key={i} className="h-32" />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<FolderKanban className="h-6 w-6" />}
          title={projects.length === 0 ? 'No projects yet' : 'No matching projects'}
          description={projects.length === 0 ? 'Create your first project to organize infrastructure.' : 'Try a different search term.'}
          action={projects.length === 0 ? <Button onClick={() => setShowCreate(true)}><Plus size={16} />New Project</Button> : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(project => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 hover:bg-zinc-800/40 hover:border-zinc-700 transition-colors duration-150 group"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <FolderKanban size={18} className="text-blue-400 shrink-0" />
                  <h3 className="text-zinc-100 font-medium group-hover:text-blue-400 transition-colors truncate">
                    {project.name}
                  </h3>
                </div>
                <Badge intent={STATUS_INTENT[project.status] ?? 'warning'}>{project.status}</Badge>
              </div>

              <p className="text-zinc-400 text-sm mb-4 line-clamp-2">
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
