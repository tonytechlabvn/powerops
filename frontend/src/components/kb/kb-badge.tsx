// Badge display component for KB achievement badges

import { Rocket, Star, Trophy } from 'lucide-react'

const BADGE_CONFIG: Record<string, { label: string; color: string; Icon: React.ElementType }> = {
  first_step: { label: 'First Step', color: 'bg-green-600/20 text-green-400 border-green-600/40', Icon: Rocket },
  terraform_practitioner: { label: 'Practitioner', color: 'bg-yellow-600/20 text-yellow-400 border-yellow-600/40', Icon: Star },
  terraform_expert: { label: 'Expert', color: 'bg-purple-600/20 text-purple-400 border-purple-600/40', Icon: Trophy },
}

export function KBBadge({ badges }: { badges: string[] }) {
  if (!badges.length) return null

  return (
    <div className="flex gap-2 flex-wrap">
      {badges.map((badge) => {
        const config = BADGE_CONFIG[badge]
        if (!config) return null
        const { label, color, Icon } = config
        return (
          <span
            key={badge}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${color}`}
            title={label}
          >
            <Icon size={12} />
            {label}
          </span>
        )
      })}
    </div>
  )
}
