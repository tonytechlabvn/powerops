// KB curriculum overview: progress summary and chapter grid

import { Link } from 'react-router-dom'
import { BookOpen, CheckCircle, Clock, Trophy, Play } from 'lucide-react'
import { useKBCurriculum } from '../../hooks/use-kb'
import { KBProgressBar } from './kb-progress-bar'
import type { ChapterSummary } from '../../types/kb-types'

const DIFFICULTY_BADGE = {
  beginner:     'bg-green-500/20 text-green-400',
  intermediate: 'bg-yellow-500/20 text-yellow-400',
  advanced:     'bg-red-500/20 text-red-400',
}

function ChapterCard({ ch }: { ch: ChapterSummary }) {
  const btnLabel = ch.status === 'completed' ? 'Review' : ch.status === 'in_progress' ? 'Continue' : 'Start'
  const btnStyle = ch.status === 'completed'
    ? 'bg-zinc-700 hover:bg-zinc-600 text-zinc-200'
    : 'bg-blue-600 hover:bg-blue-500 text-white'

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-600 font-mono">
            {String(ch.order).padStart(2, '0')}
          </span>
          {ch.status === 'completed' && <CheckCircle size={14} className="text-green-400" />}
          {ch.status === 'in_progress' && <Clock size={14} className="text-blue-400" />}
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${DIFFICULTY_BADGE[ch.difficulty]}`}>
          {ch.difficulty}
        </span>
      </div>

      <div>
        <h3 className="text-zinc-100 font-semibold text-sm leading-snug">{ch.title}</h3>
        <p className="text-zinc-500 text-xs mt-1 line-clamp-2">{ch.description}</p>
      </div>

      <div className="flex items-center gap-3 text-xs text-zinc-500">
        <span className="flex items-center gap-1">
          <Clock size={12} /> {ch.estimated_minutes}m
        </span>
        {ch.quiz_score !== null && (
          <span className="flex items-center gap-1 text-blue-400">
            Quiz: {ch.quiz_score}%
          </span>
        )}
        {ch.lab_completed && (
          <span className="text-green-400">Lab done</span>
        )}
      </div>

      <Link
        to={`/kb/${ch.slug}`}
        className={`mt-auto flex items-center justify-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${btnStyle}`}
      >
        <Play size={12} /> {btnLabel}
      </Link>
    </div>
  )
}

export function KBLandingPage() {
  const { data, isLoading, error } = useKBCurriculum()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-500">
        Loading curriculum...
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        Failed to load curriculum.
      </div>
    )
  }

  const pct = data.total_chapters > 0
    ? Math.round((data.completed / data.total_chapters) * 100)
    : 0

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen size={24} className="text-blue-400" />
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Knowledge Base</h1>
            <p className="text-zinc-400 text-sm">Learn Terraform and PowerOps step by step</p>
          </div>
        </div>
        <Link
          to="/kb/leaderboard"
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-zinc-800 text-zinc-300 hover:bg-zinc-700 text-sm transition-colors"
        >
          <Trophy size={14} className="text-yellow-400" /> Leaderboard
        </Link>
      </div>

      {/* Progress summary */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-zinc-300 font-medium">Overall Progress</span>
          <span className="text-zinc-400">
            {data.completed}/{data.total_chapters} chapters completed
          </span>
        </div>
        <KBProgressBar value={pct} />
        <div className="flex gap-6 text-xs text-zinc-500">
          <span className="text-green-400 font-medium">{data.completed} completed</span>
          <span className="text-blue-400 font-medium">{data.in_progress} in progress</span>
          <span>{data.not_started} not started</span>
          {data.avg_quiz_score !== null && (
            <span className="text-zinc-300">
              Avg quiz score: <span className="text-blue-400">{data.avg_quiz_score}%</span>
            </span>
          )}
        </div>
      </div>

      {/* Chapter grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.chapters.map((ch) => (
          <ChapterCard key={ch.slug} ch={ch} />
        ))}
      </div>
    </div>
  )
}
