/**
 * Swimmer List Component
 * ======================
 * Display detailed list of all tracked swimmers with all their data
 */

import type { Swimmer } from '../../types/swimmer'
import { TRACK_COLORS } from '../../utils/constants'

interface SwimmerListProps {
  swimmers: Swimmer[]
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function calculateTimeInView(firstSeen: string, lastSeen: string): string {
  const first = new Date(firstSeen).getTime()
  const last = new Date(lastSeen).getTime()
  const seconds = (last - first) / 1000
  return formatTime(seconds)
}

export default function SwimmerList({ swimmers }: SwimmerListProps) {
  if (swimmers.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Tracked Swimmers</h3>
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">👁️</div>
          <p>No swimmers detected yet</p>
          <p className="text-sm mt-1">Waiting for AI pipeline data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg">
      <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-primary-50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900 flex items-center">
            <span className="mr-2">📊</span>
            Active Swimmers ({swimmers.length})
          </h3>
          <div className="text-sm text-gray-600">
            Last updated: {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Track ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Position
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Confidence
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Time in View
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {swimmers.map((swimmer) => {
              const color = TRACK_COLORS[swimmer.track_id % TRACK_COLORS.length]
              const timeInView = calculateTimeInView(swimmer.first_seen, swimmer.last_seen)
              
              return (
                <tr key={swimmer.track_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center">
                      <div
                        className="w-4 h-4 rounded-full mr-2"
                        style={{ backgroundColor: color }}
                      />
                      <span className="font-mono font-bold text-gray-900">
                        #{swimmer.track_id}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      <div>X: {swimmer.bbox.x1}-{swimmer.bbox.x2}</div>
                      <div className="text-xs text-gray-500">
                        Y: {swimmer.bbox.y1}-{swimmer.bbox.y2}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                        <div
                          className="bg-green-600 h-2 rounded-full"
                          style={{ width: `${swimmer.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {(swimmer.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-sm text-gray-900 font-mono">
                      {timeInView}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        swimmer.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : swimmer.status === 'alerted'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {swimmer.status}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

