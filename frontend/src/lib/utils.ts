// Shared utility functions: classname helper, formatting, status colors

import { format, formatDistanceToNow } from 'date-fns'
import type { JobStatus, ApprovalStatus, ResourceAction } from '../types/api-types'

/** Merge class names, filtering falsy values */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}

/** Format ISO date string to human-readable form */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return format(new Date(iso), 'MMM d, yyyy HH:mm')
  } catch {
    return iso
  }
}

/** Format ISO date as relative time ("3 minutes ago") */
export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true })
  } catch {
    return iso
  }
}

/** Format cost estimate string for display */
export function formatCost(cost: string | null | undefined): string {
  if (!cost) return 'N/A'
  return cost
}

/** Tailwind color classes for job status badges */
export function statusColor(status: JobStatus): string {
  switch (status) {
    case 'running':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    case 'completed':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 'failed':
      return 'bg-red-500/20 text-red-400 border-red-500/30'
    case 'pending':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    case 'cancelled':
      return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
    default:
      return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
  }
}

/** Tailwind color classes for approval status */
export function approvalStatusColor(status: ApprovalStatus): string {
  switch (status) {
    case 'approved':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 'rejected':
      return 'bg-red-500/20 text-red-400 border-red-500/30'
    case 'pending':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    default:
      return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
  }
}

/** Tailwind color classes for resource change actions in plan diff */
export function actionColor(action: ResourceAction): string {
  switch (action) {
    case 'create':
      return 'text-green-400'
    case 'delete':
      return 'text-red-400'
    case 'update':
      return 'text-yellow-400'
    case 'replace':
      return 'text-orange-400'
    case 'no-op':
      return 'text-zinc-500'
    default:
      return 'text-zinc-400'
  }
}

/** Short symbol for resource change action */
export function actionSymbol(action: ResourceAction): string {
  switch (action) {
    case 'create':  return '+'
    case 'delete':  return '-'
    case 'update':  return '~'
    case 'replace': return '±'
    case 'no-op':   return ' '
    default:        return '?'
  }
}
