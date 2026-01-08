/**
 * Detailed Statistics Component
 * ==============================
 * Show comprehensive tracking statistics
 */

import type { Swimmer } from '../../types/swimmer'

interface DetailedStatsProps {
  swimmers: Swimmer[]
}

export default function DetailedStats({ swimmers }: DetailedStatsProps) {
  // Calculate statistics
  const totalSwimmers = swimmers.length
  const avgConfidence = swimmers.length > 0
    ? swimmers.reduce((sum, s) => sum + s.confidence, 0) / swimmers.length
    : 0

  const totalTimeInView = swimmers.reduce((sum, swimmer) => {
    const first = new Date(swimmer.first_seen).getTime()
    const last = new Date(swimmer.last_seen).getTime()
    return sum + (last - first) / 1000
  }, 0)

  const avgTimeInView = swimmers.length > 0
    ? totalTimeInView / swimmers.length
    : 0

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-lg p-6 text-white">
        <div className="text-3xl font-bold">{totalSwimmers}</div>
        <div className="text-sm opacity-90 mt-1">Active Swimmers</div>
        <div className="text-xs opacity-75 mt-2">Currently being tracked</div>
      </div>

      <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg shadow-lg p-6 text-white">
        <div className="text-3xl font-bold">{(avgConfidence * 100).toFixed(1)}%</div>
        <div className="text-sm opacity-90 mt-1">Avg Confidence</div>
        <div className="text-xs opacity-75 mt-2">Detection accuracy</div>
      </div>

      <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow-lg p-6 text-white">
        <div className="text-3xl font-bold">{formatTime(avgTimeInView)}</div>
        <div className="text-sm opacity-90 mt-1">Avg Time in View</div>
        <div className="text-xs opacity-75 mt-2">Per swimmer</div>
      </div>

      <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg shadow-lg p-6 text-white">
        <div className="text-3xl font-bold">{formatTime(totalTimeInView)}</div>
        <div className="text-sm opacity-90 mt-1">Total Tracked Time</div>
        <div className="text-xs opacity-75 mt-2">Combined duration</div>
      </div>
    </div>
  )
}


