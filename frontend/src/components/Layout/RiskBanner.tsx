/**
 * One patrol-wide risk state. Sits under the header so it stays visible
 * while the operator scrolls the video and the track table.
 */

import type { PatrolState } from '../../utils/patrolRisk'

const COPY: Record<PatrolState, { title: string; detail: string; className: string }> = {
  idle: {
    title: 'Standby',
    detail: 'Upload a patrol clip to start detection. Nothing is being scored yet.',
    className: 'border-slate-600/80 bg-slate-900/80 text-slate-200',
  },
  clear: {
    title: 'Clear',
    detail: 'No open watch, alert, or emergency. Keep watching the water.',
    className: 'border-emerald-500/40 bg-emerald-950/50 text-emerald-50',
  },
  analyzing: {
    title: 'Analyzing',
    detail: 'The model is reading the clip. Tracks appear as soon as the first frame lands.',
    className: 'border-sky-500/40 bg-sky-950/50 text-sky-50',
  },
  watch: {
    title: 'Watch',
    detail: 'At least one track or alert needs a closer look. It is not an emergency yet.',
    className: 'border-amber-400/50 bg-amber-950/55 text-amber-50',
  },
  alert: {
    title: 'Alert',
    detail: 'A priority alert is open. Acknowledge it or focus the track on the video.',
    className: 'border-orange-500/55 bg-orange-950/60 text-orange-50',
  },
  emergency: {
    title: 'Emergency',
    detail: 'An unacknowledged emergency is open. Treat the video as a prompt to look at the water, not as a rescue decision.',
    className: 'border-red-500/70 bg-red-950/70 text-red-50',
  },
  offline: {
    title: 'Offline',
    detail: 'The dashboard cannot reach the API or the live feed. Check VITE_API_URL and that the backend is running.',
    className: 'border-rose-500/50 bg-rose-950/60 text-rose-50',
  },
}

interface RiskBannerProps {
  state: PatrolState
}

export default function RiskBanner({ state }: RiskBannerProps) {
  const copy = COPY[state]
  return (
    <div
      className={`border-b px-4 py-3 sm:px-8 ${copy.className}`}
      role="status"
      aria-live="polite"
    >
      <div className="mx-auto flex max-w-[1680px] flex-wrap items-baseline gap-x-4 gap-y-1">
        <p className="text-sm font-semibold uppercase tracking-[0.16em]">{copy.title}</p>
        <p className="text-sm leading-relaxed opacity-90">{copy.detail}</p>
      </div>
    </div>
  )
}
