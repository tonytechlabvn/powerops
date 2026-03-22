// Team management panel: member table with role badges + add/remove actions

import { useState } from 'react'
import { UserPlus, Trash2, X } from 'lucide-react'
import { apiClient } from '../../services/api-client'
import type { ProjectMember } from '../../types/api-types'

interface Props {
  projectId: string
  members: ProjectMember[]
  onMembersChange: () => void
}

interface AddMemberForm {
  user_id: string
  role_name: string
  module_patterns: string  // comma-separated
}

const ROLE_COLORS: Record<string, string> = {
  'workspace-admin': 'bg-purple-500/20 text-purple-400',
  'operator': 'bg-blue-500/20 text-blue-400',
  'planner': 'bg-cyan-500/20 text-cyan-400',
  'viewer': 'bg-zinc-500/20 text-zinc-400',
}

function roleBadgeClass(role: string): string {
  return ROLE_COLORS[role] ?? 'bg-zinc-500/20 text-zinc-400'
}

export function TeamManagementPanel({ projectId, members, onMembersChange }: Props) {
  const [showDialog, setShowDialog] = useState(false)
  const [form, setForm] = useState<AddMemberForm>({
    user_id: '',
    role_name: 'viewer',
    module_patterns: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!form.user_id.trim()) {
      setError('User ID is required')
      return
    }
    setSubmitting(true)
    try {
      const assigned_modules = form.module_patterns
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
      await apiClient.post(`/api/projects/${projectId}/members`, {
        user_id: form.user_id.trim(),
        role_name: form.role_name,
        assigned_modules,
      })
      setShowDialog(false)
      setForm({ user_id: '', role_name: 'viewer', module_patterns: '' })
      onMembersChange()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to add member')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRemove(userId: string) {
    if (!confirm('Remove this member from the project?')) return
    try {
      await apiClient.del(`/api/projects/${projectId}/members/${userId}`)
      onMembersChange()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to remove member')
    }
  }

  return (
    <div>
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-zinc-400 text-sm">{members.length} member{members.length !== 1 ? 's' : ''}</span>
        <button
          onClick={() => setShowDialog(true)}
          className="flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-md transition-colors"
        >
          <UserPlus size={14} />
          Add Member
        </button>
      </div>

      {/* Member table */}
      {members.length === 0 ? (
        <div className="text-zinc-500 text-sm py-4">No team members yet.</div>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-4 py-3 font-medium">Member</th>
                <th className="text-left px-4 py-3 font-medium">Role</th>
                <th className="text-left px-4 py-3 font-medium">Module Scope</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {members.map(member => (
                <tr key={member.user_id} className="border-b border-zinc-800/50 last:border-0">
                  <td className="px-4 py-3">
                    <div className="text-zinc-100">{member.user_name || member.user_email}</div>
                    <div className="text-xs text-zinc-500">{member.user_email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${roleBadgeClass(member.role_name)}`}>
                      {member.role_name}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">
                    {member.assigned_modules.length > 0
                      ? member.assigned_modules.join(', ')
                      : <span className="italic">All modules</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRemove(member.user_id)}
                      className="text-zinc-600 hover:text-red-400 transition-colors"
                      title="Remove member"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Member dialog */}
      {showDialog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-zinc-100 font-semibold">Add Team Member</h2>
              <button
                onClick={() => { setShowDialog(false); setError(null) }}
                className="text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-zinc-400 text-xs mb-1.5">User ID</label>
                <input
                  type="text"
                  value={form.user_id}
                  onChange={e => setForm(f => ({ ...f, user_id: e.target.value }))}
                  placeholder="User UUID"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-zinc-400 text-xs mb-1.5">Role</label>
                <select
                  value={form.role_name}
                  onChange={e => setForm(f => ({ ...f, role_name: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="workspace-admin">workspace-admin</option>
                  <option value="operator">operator</option>
                  <option value="planner">planner</option>
                  <option value="viewer">viewer</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 text-xs mb-1.5">
                  Module Scope
                  <span className="text-zinc-600 ml-1">(comma-separated patterns, blank = all)</span>
                </label>
                <input
                  type="text"
                  value={form.module_patterns}
                  onChange={e => setForm(f => ({ ...f, module_patterns: e.target.value }))}
                  placeholder="aws-*, prod-database"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              {error && (
                <p className="text-red-400 text-xs">{error}</p>
              )}

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => { setShowDialog(false); setError(null) }}
                  className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-md transition-colors"
                >
                  {submitting ? 'Adding...' : 'Add Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
