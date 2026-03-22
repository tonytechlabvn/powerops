// Sidebar chapter list navigation for KB pages

import { NavLink } from 'react-router-dom'
import { CheckCircle, Circle, Clock } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { ChapterSummary } from '../../types/kb-types'

interface KBChapterNavProps {
  chapters: ChapterSummary[]
  currentSlug?: string
}

const DIFFICULTY_COLORS = {
  beginner: 'text-green-400',
  intermediate: 'text-yellow-400',
  advanced: 'text-red-400',
}

function StatusIcon({ status }: { status: ChapterSummary['status'] }) {
  if (status === 'completed') return <CheckCircle size={14} className="text-green-400 shrink-0" />
  if (status === 'in_progress') return <Clock size={14} className="text-blue-400 shrink-0" />
  return <Circle size={14} className="text-zinc-600 shrink-0" />
}

export function KBChapterNav({ chapters, currentSlug }: KBChapterNavProps) {
  return (
    <nav className="w-56 shrink-0 flex flex-col gap-0.5 overflow-y-auto">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider px-2 pb-2">
        Chapters
      </p>
      {chapters.map((ch) => (
        <NavLink
          key={ch.slug}
          to={`/kb/${ch.slug}`}
          className={cn(
            'flex items-start gap-2 px-2 py-2 rounded-md text-sm transition-colors',
            currentSlug === ch.slug
              ? 'bg-blue-600/20 text-blue-400'
              : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800',
          )}
        >
          <span className="text-xs text-zinc-600 w-4 shrink-0 pt-0.5 font-mono">
            {String(ch.order).padStart(2, '0')}
          </span>
          <StatusIcon status={ch.status} />
          <span className="flex-1 leading-snug">{ch.title}</span>
          <span className={cn('text-xs shrink-0', DIFFICULTY_COLORS[ch.difficulty])}>
            {ch.difficulty[0].toUpperCase()}
          </span>
        </NavLink>
      ))}
    </nav>
  )
}
