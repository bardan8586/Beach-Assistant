/**
 * Swimmer List Component
 * ======================
 * Display detailed list of all tracked swimmers with all their data
 */

import type { Swimmer, BoundingBox } from '../../types/swimmer'
import { TRACK_COLORS } from '../../utils/constants'

interface SwimmerListProps {
  swimmers: Swimmer[]
}

/** Normalize bbox to x1,y1,x2,y2 for display (API may send x,y,w,h). */
function bboxForDisplay(bbox: BoundingBox): { x1: number; y1: number; x2: number; y2: number } {
  if (bbox.x1 != null && bbox.y1 != null && bbox.x2 != null && bbox.y2 != null) {
    return { x1: bbox.x1, y1: bbox.y1, x2: bbox.x2, y2: bbox.y2 }
  }
  const x = bbox.x ?? 0
  const y = bbox.y ?? 0
  const w = bbox.w ?? 0
  const h = bbox.h ?? 0
  return { x1: x, y1: y, x2: x + w, y2: y + h }
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
      <section className="card p-6" aria-label="Tracked swimmers">
        <h3 className="card-title-lg mb-4">Tracked Swimmers</h3>
        <div className="py-8 text-center text-slate-500">
          <div className="text-4xl mb-2">👁️</div>
          <p>No swimmers detected yet</p>
          <p className="mt-1 text-sm">Waiting for AI pipeline data…</p>
        </div>
      </section>
    )
  }

  return (
    <section className="card overflow-hidden" aria-label="Active swimmers">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50/50 px-4 py-3">
        <h3 className="card-title-lg flex items-center gap-2">
          <span aria-hidden>📊</span>
          Active Swimmers ({swimmers.length})
        </h3>
        <div className="text-sm text-slate-600">Updated {new Date().toLocaleTimeString()}</div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600">
                Track ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600">
                Position
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600">
                Confidence
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600">
                Time in View
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {swimmers.map((swimmer) => {
              const color = TRACK_COLORS[swimmer.track_id % TRACK_COLORS.length]
              const timeInView = calculateTimeInView(swimmer.first_seen, swimmer.last_seen)
              const box = bboxForDisplay(swimmer.bbox)

              return (
                <tr key={swimmer.track_id} className="transition-colors hover:bg-slate-50">
                  <td className="whitespace-nowrap px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-4 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                      <span className="font-mono font-semibold text-slate-900">#{swimmer.track_id}</span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <div className="text-sm text-slate-900">
                      <div>X: {box.x1.toFixed(0)}–{box.x2.toFixed(0)}</div>
                      <div className="text-xs text-slate-500">Y: {box.y1.toFixed(0)}–{box.y2.toFixed(0)}</div>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-24 rounded-full bg-slate-200">
                        <div className="h-2 rounded-full bg-emerald-600" style={{ width: `${swimmer.confidence * 100}%` }} />
                      </div>
                      <span className="text-sm font-medium text-slate-900">{(swimmer.confidence * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span className="font-mono text-sm text-slate-900">{timeInView}</span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      className={`status-pill ${
                        swimmer.status === 'active'
                          ? 'bg-emerald-100 text-emerald-800'
                          : swimmer.status === 'alerted'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-slate-100 text-slate-800'
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
    </section>
  )
}


