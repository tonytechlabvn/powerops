// Sortable table of past Terraform jobs

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronUp, ChevronDown } from 'lucide-react'
import type { Job } from '../../types/api-types'
import { statusColor, formatDate, formatRelative } from '../../lib/utils'

type SortKey = 'created_at' | 'status' | 'type' | 'workspace'
type SortDir = 'asc' | 'desc'

interface JobHistoryTableProps {
  jobs: Job[]
}

function SortIcon({ col, sortKey, sortDir }: { col: SortKey; sortKey: SortKey; sortDir: SortDir }) {
  if (col !== sortKey) return <ChevronUp size={12} className="text-zinc-600" />
  return sortDir === 'asc'
    ? <ChevronUp size={12} className="text-blue-400" />
    : <ChevronDown size={12} className="text-blue-400" />
}

function getJobSortValue(job: Job, key: SortKey): string {
  return job[key] ?? ''
}

export function JobHistoryTable({ jobs }: JobHistoryTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sorted = [...jobs].sort((a, b) => {
    const av = getJobSortValue(a, sortKey)
    const bv = getJobSortValue(b, sortKey)
    const cmp = av.localeCompare(bv)
    return sortDir === 'asc' ? cmp : -cmp
  })

  const columns: { key: SortKey; label: string }[] = [
    { key: 'workspace',  label: 'Workspace' },
    { key: 'type',       label: 'Type' },
    { key: 'status',     label: 'Status' },
    { key: 'created_at', label: 'Started' },
  ]

  if (jobs.length === 0) {
    return <p className="text-sm text-zinc-500">No jobs found.</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-800 text-zinc-400 text-xs uppercase tracking-wider">
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                className="px-4 py-3 text-left cursor-pointer hover:text-zinc-200 select-none"
                onClick={() => toggleSort(col.key)}
              >
                <span className="flex items-center gap-1">
                  {col.label}
                  <SortIcon col={col.key} sortKey={sortKey} sortDir={sortDir} />
                </span>
              </th>
            ))}
            <th className="px-4 py-3 text-left text-xs uppercase tracking-wider">Completed</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800 bg-zinc-900">
          {sorted.map(job => (
            <tr key={job.id} className="hover:bg-zinc-800/50 transition-colors">
              <td className="px-4 py-3 text-zinc-200 font-mono text-xs max-w-xs truncate">
                {job.workspace}
              </td>
              <td className="px-4 py-3 text-zinc-400 capitalize">{job.type}</td>
              <td className="px-4 py-3">
                <span className={`text-xs px-2 py-0.5 rounded border ${statusColor(job.status)}`}>
                  {job.status}
                </span>
              </td>
              <td className="px-4 py-3 text-zinc-400 text-xs whitespace-nowrap">
                {formatDate(job.created_at)}
              </td>
              <td className="px-4 py-3 text-zinc-500 text-xs whitespace-nowrap">
                {job.completed_at ? formatRelative(job.completed_at) : '—'}
              </td>
              <td className="px-4 py-3 text-right">
                <Link
                  to={`/jobs/${job.id}`}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
