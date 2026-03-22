// Color-coded risk level badge for plan analysis display.

interface PlanRiskBadgeProps {
  level: 'low' | 'medium' | 'high' | 'critical' | string
  showLabel?: boolean
  size?: 'sm' | 'md'
}

const RISK_STYLES: Record<string, string> = {
  low:      'bg-green-900/40 text-green-400 border-green-700/50',
  medium:   'bg-yellow-900/40 text-yellow-400 border-yellow-700/50',
  high:     'bg-orange-900/40 text-orange-400 border-orange-700/50',
  critical: 'bg-red-900/40 text-red-400 border-red-600/60 animate-pulse',
}

const RISK_ICONS: Record<string, string> = {
  low: '✓', medium: '⚠', high: '⚠', critical: '✕',
}

export function PlanRiskBadge({ level, showLabel = true, size = 'md' }: PlanRiskBadgeProps) {
  const style = RISK_STYLES[level] ?? RISK_STYLES.medium
  const icon = RISK_ICONS[level] ?? '?'
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm'
  const padding = size === 'sm' ? 'px-2 py-0.5' : 'px-3 py-1'

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-medium
                      ${style} ${textSize} ${padding}`}>
      <span>{icon}</span>
      {showLabel && <span className="capitalize">{level} risk</span>}
    </span>
  )
}
