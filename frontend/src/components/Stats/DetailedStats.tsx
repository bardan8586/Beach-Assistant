/**
 * Detailed Statistics Component
 * ==============================
 * Clean, scannable stats for lifeguard dashboard
 */

import type { Swimmer } from '../../types/swimmer'

interface DetailedStatsProps {
  swimmers: Swimmer[]
}

function StatCard({
  value,
  label,
  sublabel,
  accent = 'slate',
}: {
  value: string | number
  label: string
  sublabel?: string
  accent?: 'blue' | 'emerald' | 'slate' | 'amber'
}) {
  const accentBorder = {
    blue: 'border-l-blue-500',
    emerald: 'border-l-emerald-500',
    slate: 'border-l-slate-400',
    amber: 'border-l-amber-500',
  }[accent]
  return (
    <div className={`card border-l-4 p-5 tabular-nums ${accentBorder} animate-fade-in`}>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="mt-0.5 text-sm font-medium text-slate-600">{label}</div>
      {sublabel && <div className="mt-1 text-xs text-slate-400">{sublabel}</div>}
    </div>
  )
}

export default function DetailedStats({ swimmers }: DetailedStatsProps) {
  const totalSwimmers = swimmers.length
  const avgConfidence =
    swimmers.length > 0
      ? swimmers.reduce((sum, s) => sum + (s.confidence ?? 0), 0) / swimmers.length
      : 0
  const totalTimeInView = swimmers.reduce((sum, swimmer) => {
    const first = new Date(swimmer.first_seen).getTime()
    const last = new Date(swimmer.last_seen).getTime()
    return sum + (last - first) / 1000
  }, 0)
  const avgTimeInView = swimmers.length > 0 ? totalTimeInView / swimmers.length : 0

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        value={totalSwimmers}
        label="Active Swimmers"
        sublabel="Currently tracked"
        accent="blue"
      />
      <StatCard
        value={`${(avgConfidence * 100).toFixed(1)}%`}
        label="Avg Confidence"
        sublabel="Detection accuracy"
        accent="emerald"
      />
      <StatCard
        value={formatTime(avgTimeInView)}
        label="Avg Time in View"
        sublabel="Per swimmer"
        accent="slate"
      />
      <StatCard
        value={formatTime(totalTimeInView)}
        label="Total Tracked Time"
        sublabel="Combined"
        accent="amber"
      />
    </div>
  )
}
