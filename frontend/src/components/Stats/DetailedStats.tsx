/**
 * Situation overview — KPI strip (dense, readable).
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
  accent?: 'cyan' | 'emerald' | 'slate' | 'amber'
}) {
  const bar = {
    cyan: 'from-cyan-400 to-sky-600',
    emerald: 'from-emerald-400 to-teal-600',
    slate: 'from-slate-400 to-slate-600',
    amber: 'from-amber-400 to-orange-500',
  }[accent]
  return (
    <div
      className="card card-elevated relative overflow-hidden p-5 sm:p-6 cc-enter"
      style={{ borderRadius: 'var(--radius-card)' }}
    >
      <div className={`absolute left-0 right-0 top-0 h-0.5 bg-gradient-to-r ${bar}`} aria-hidden />
      <div className="pt-1 text-3xl font-bold tabular-nums tracking-tight text-slate-50 sm:text-4xl">{value}</div>
      <div className="mt-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</div>
      {sublabel ? <div className="mt-1 text-xs text-slate-500">{sublabel}</div> : null}
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
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-5">
      <StatCard value={totalSwimmers} label="Active tracks" sublabel="Current feed" accent="cyan" />
      <StatCard
        value={`${(avgConfidence * 100).toFixed(1)}%`}
        label="Mean confidence"
        sublabel="Across detections"
        accent="emerald"
      />
      <StatCard value={formatTime(avgTimeInView)} label="Avg. time in view" sublabel="Per track" accent="slate" />
      <StatCard value={formatTime(totalTimeInView)} label="Cumulative time" sublabel="All tracks" accent="amber" />
    </div>
  )
}
