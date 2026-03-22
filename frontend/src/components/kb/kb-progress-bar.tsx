// Reusable progress bar for KB chapter/overall completion display

interface KBProgressBarProps {
  value: number
  label?: string
  size?: 'sm' | 'md'
}

export function KBProgressBar({ value, label, size = 'md' }: KBProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value))
  const trackH = size === 'sm' ? 'h-1.5' : 'h-2.5'
  const textSz = size === 'sm' ? 'text-xs' : 'text-sm'

  return (
    <div className="w-full">
      {label && (
        <div className={`flex justify-between mb-1 ${textSz} text-zinc-400`}>
          <span>{label}</span>
          <span className="text-zinc-300 font-medium">{clamped}%</span>
        </div>
      )}
      <div className={`w-full ${trackH} bg-zinc-700 rounded-full overflow-hidden`}>
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-300"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}
