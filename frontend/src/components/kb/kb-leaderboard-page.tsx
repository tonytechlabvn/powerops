// Leaderboard page — team and org rankings for KB curriculum

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Trophy } from 'lucide-react'
import { useKBLeaderboard } from '../../hooks/use-kb'
import { useAuth } from '../auth/auth-provider'
import { KBLeaderboardCard } from './kb-leaderboard-card'

const SCOPES = ['team', 'org'] as const

export function KBLeaderboardPage() {
  const [scope, setScope] = useState<'team' | 'org'>('team')
  const { data, isLoading } = useKBLeaderboard(scope)
  const { user } = useAuth()
  const currentUserId = user?.id || ''

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/kb" className="text-zinc-400 hover:text-zinc-100 transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <Trophy size={24} className="text-yellow-400" />
          <h1 className="text-2xl font-bold text-zinc-100">Leaderboard</h1>
        </div>

        {/* Scope tabs */}
        <div className="flex rounded-lg border border-zinc-700 overflow-hidden">
          {SCOPES.map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={`px-4 py-1.5 text-sm font-medium capitalize transition-colors ${
                scope === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:text-zinc-100'
              }`}
            >
              {s === 'team' ? 'My Team' : 'Organization'}
            </button>
          ))}
        </div>
      </div>

      {/* Current user rank */}
      {data?.current_user_rank && (
        <div className="text-sm text-zinc-400">
          Your rank: <span className="text-blue-400 font-bold">#{data.current_user_rank}</span>
        </div>
      )}

      {/* Entries */}
      {isLoading ? (
        <div className="text-zinc-500 text-center py-12">Loading leaderboard...</div>
      ) : !data?.entries.length ? (
        <div className="text-center py-16 space-y-2">
          <Trophy size={48} className="text-zinc-700 mx-auto" />
          <p className="text-zinc-400">No one has started the Knowledge Base yet.</p>
          <p className="text-zinc-500 text-sm">Be the first!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.entries.map((entry, i) => (
            <KBLeaderboardCard
              key={entry.user_id}
              entry={entry}
              rank={i + 1}
              isCurrentUser={entry.user_id === currentUserId}
            />
          ))}
        </div>
      )}
    </div>
  )
}
