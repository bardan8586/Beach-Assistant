/**
 * Tracked swimmers — dense operational table.
 */

import type { Swimmer, BoundingBox } from '../../types/swimmer'
import { TRACK_COLORS } from '../../utils/constants'

interface SwimmerListProps {
  swimmers: Swimmer[]
}

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
      <section className="card card-elevated p-8 sm:p-10 cc-enter" aria-label="Tracked swimmers">
        <div className="border-b border-slate-700/50 pb-4">
          <p className="card-title">Tracks</p>
          <h3 className="card-title-lg mt-1">Active swimmers</h3>
        </div>
        <div className="py-14 text-center">
          <p className="text-sm font-medium text-slate-300">No active tracks</p>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-500">
            Run analysis or connect a feed. Rows appear when the pipeline publishes swimmer data.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="card card-elevated overflow-hidden cc-enter" aria-label="Active swimmers">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-700/50 bg-slate-950/30 px-5 py-4 sm:px-6">
        <div>
          <p className="card-title">Tracks</p>
          <h3 className="card-title-lg mt-0.5">Active swimmers ({swimmers.length})</h3>
        </div>
        <div className="text-xs font-medium tabular-nums text-slate-500">Updated {new Date().toLocaleTimeString()}</div>
      </div>

      <div className="overflow-x-auto">
        <table className="table-ops w-full min-w-[640px] text-sm text-slate-300">
          <thead>
            <tr>
              <th className="px-5 py-3 text-left sm:px-6">Track</th>
              <th className="px-5 py-3 text-left sm:px-6">BBox</th>
              <th className="px-5 py-3 text-left sm:px-6">Confidence</th>
              <th className="px-5 py-3 text-left sm:px-6">In view</th>
              <th className="px-5 py-3 text-left sm:px-6">Status</th>
            </tr>
          </thead>
          <tbody>
            {swimmers.map((swimmer) => {
              const { x1, y1, x2, y2 } = bboxForDisplay(swimmer.bbox)
              const color = TRACK_COLORS[swimmer.track_id % TRACK_COLORS.length]
              return (
                <tr key={swimmer.track_id}>
                  <td className="px-5 py-3.5 font-mono text-xs font-semibold text-slate-100 sm:px-6 sm:text-sm">
                    <span className="mr-2 inline-block h-2 w-2 rounded-full align-middle" style={{ backgroundColor: color }} />
                    {swimmer.track_id}
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-500 sm:px-6">
                    {x1},{y1} → {x2},{y2}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-slate-200 sm:px-6">
                    {((swimmer.confidence ?? 0) * 100).toFixed(1)}%
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-500 sm:px-6">
                    {calculateTimeInView(swimmer.first_seen, swimmer.last_seen)}
                  </td>
                  <td className="px-5 py-3.5 sm:px-6">
                    <span className="inline-flex rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-300 ring-1 ring-emerald-500/30">
                      {swimmer.status ?? 'active'}
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
