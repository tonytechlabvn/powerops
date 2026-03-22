// Single leaderboard entry card

import { KBBadge } from './kb-badge'
import type { LeaderboardEntry } from '../../types/kb-types'

interface Props {
  entry: LeaderboardEntry
  rank: number
  isCurrentUser: boolean
}

export function KBLeaderboardCard({ entry, rank, isCurrentUser }: Props) {
  return (
    <div
      className={`flex items-center gap-4 px-4 py-3 rounded-lg border ${
        isCurrentUser
          ? 'border-blue-500/50 bg-blue-600/10'
          : 'border-zinc-800 bg-zinc-900'
      }`}
    >
      {/* Rank */}
      <span className={`text-lg font-bold w-8 text-center ${
        rank <= 3 ? 'text-yellow-400' : 'text-zinc-500'
      }`}>
        #{rank}
      </span>

      {/* Avatar initials */}
      <div className="w-9 h-9 rounded-full bg-zinc-700 flex items-center justify-center text-sm font-medium text-zinc-300 shrink-0">
        {(entry.display_name || '?')[0].toUpperCase()}
      </div>

      {/* Name + badges */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`font-medium truncate ${isCurrentUser ? 'text-blue-400' : 'text-zinc-100'}`}>
            {entry.display_name}
          </span>
          {isCurrentUser && <span className="text-xs text-blue-400/70">(you)</span>}
        </div>
        <KBBadge badges={entry.badges} />
      </div>

      {/* Stats */}
      <div className="flex gap-6 text-sm text-zinc-400 shrink-0">
        <div className="text-center">
          <div className="text-zinc-100 font-medium">{entry.chapters_completed}</div>
          <div className="text-xs">Chapters</div>
        </div>
        <div className="text-center">
          <div className="text-zinc-100 font-medium">{entry.avg_quiz_score}%</div>
          <div className="text-xs">Avg Score</div>
        </div>
        <div className="text-center">
          <div className="text-zinc-100 font-medium">{entry.labs_completed}</div>
          <div className="text-xs">Labs</div>
        </div>
        <div className="text-center">
          <div className="text-blue-400 font-bold">{entry.total_score}</div>
          <div className="text-xs">Points</div>
        </div>
      </div>
    </div>
  )
}
