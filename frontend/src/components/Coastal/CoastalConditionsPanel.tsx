/**
 * Live coastal context — waves, swell, SST, wind via backend Open-Meteo proxy.
 */

import { useCallback, useEffect, useState } from 'react'
import { apiService } from '../../services/api'
import type { CoastalConditionsResponse } from '../../types/coastal'

function fmt(n: number | null | undefined, digits = 1, suffix = ''): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return `${n.toFixed(digits)}${suffix}`
}

function windCompass(deg: number | null | undefined): string {
  if (deg === null || deg === undefined) return ''
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  const i = Math.round(deg / 45) % 8
  return dirs[i]
}

/** Open-Meteo WMO weather code (subset) — https://open-meteo.com/en/docs */
function wmoLabel(code: number | null | undefined): string {
  if (code === null || code === undefined) return ''
  const m: Record<number, string> = {
    0: 'Clear',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Fog',
    48: 'Fog',
    51: 'Light drizzle',
    53: 'Drizzle',
    55: 'Dense drizzle',
    61: 'Light rain',
    63: 'Rain',
    65: 'Heavy rain',
    71: 'Snow',
    80: 'Rain showers',
    81: 'Showers',
    82: 'Heavy showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm',
    99: 'Thunderstorm',
  }
  return m[code] ?? `Code ${code}`
}

function StatCard({
  label,
  value,
  sub,
  accent = 'sky',
}: {
  label: string
  value: string
  sub?: string
  accent?: 'sky' | 'cyan' | 'violet' | 'amber' | 'emerald' | 'rose'
}) {
  const ring = {
    sky: 'from-sky-400/30 to-blue-600/10',
    cyan: 'from-cyan-400/30 to-teal-700/10',
    violet: 'from-violet-400/25 to-indigo-800/10',
    amber: 'from-amber-400/25 to-orange-900/15',
    emerald: 'from-emerald-400/25 to-teal-900/10',
    rose: 'from-rose-400/25 to-red-900/15',
  }[accent]
  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-white/15 bg-white/[0.07] p-4 backdrop-blur-md shadow-inner`}
      style={{ borderRadius: 'var(--radius-card)' }}
    >
      <div
        className={`pointer-events-none absolute inset-0 bg-gradient-to-br opacity-90 ${ring}`}
        aria-hidden
      />
      <div className="relative">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-300">{label}</div>
        <div className="mt-1.5 text-2xl font-bold tabular-nums tracking-tight text-white sm:text-3xl">{value}</div>
        {sub ? <div className="mt-1 text-xs text-slate-300">{sub}</div> : null}
      </div>
    </div>
  )
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" aria-busy="true" aria-label="Loading coastal data">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-[5.5rem] animate-pulse rounded-xl border border-white/10 bg-white/5 sm:h-[6rem]"
          style={{ borderRadius: 'var(--radius-card)' }}
        />
      ))}
    </div>
  )
}

export default function CoastalConditionsPanel() {
  const [data, setData] = useState<CoastalConditionsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiService.getCoastalConditions()
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load coastal data')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 15 * 60 * 1000)
    return () => window.clearInterval(id)
  }, [load])

  const wx = data?.weather
  const wxLine =
    wx?.weather_code != null && wx.weather_code !== undefined
      ? wmoLabel(wx.weather_code)
      : null
  const dayNight = wx?.is_day === 0 ? 'Night' : wx?.is_day === 1 ? 'Day' : null

  return (
    <section
      className="cc-coastal-frame relative overflow-hidden"
      style={{ borderRadius: 'var(--radius-card)' }}
      aria-label="Live coastal conditions"
    >
      <div
        className="absolute inset-0 opacity-[0.94]"
        style={{
          background:
            'linear-gradient(145deg, rgb(15 23 42) 0%, rgb(30 41 95) 38%, rgb(8 47 73) 72%, rgb(14 116 144) 100%)',
        }}
      />
      <div className="relative p-5 text-white sm:p-6">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold tracking-tight sm:text-xl">Live coastal context</h2>
              <span className="rounded-full border border-emerald-400/40 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-200">
                Open-Meteo
              </span>
            </div>
            <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-slate-300">
              <span className="font-medium text-white">{data?.location.label ?? 'Patrol area'}</span>
              {' — '}
              waves, swell, sea surface temperature, and surface wind for situational awareness next to your CV feed.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="shrink-0 rounded-lg border border-white/25 bg-white/10 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
            style={{ borderRadius: 'var(--radius-button)' }}
          >
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="mb-4 rounded-lg border border-red-400/35 bg-red-950/40 px-4 py-3 text-sm text-red-100"
          >
            {error}
          </div>
        )}

        {data && !loading && data.partial && data.warnings.length > 0 && (
          <p className="mb-3 text-xs text-amber-200/95">Partial data: {data.warnings.join(' · ')}</p>
        )}

        {loading && !data ? <SkeletonGrid /> : null}

        {(!loading || data) && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard
              accent="sky"
              label="Significant wave"
              value={fmt(data?.marine.wave_height_m, 2, ' m')}
              sub={
                data?.marine.wave_direction_deg != null
                  ? `${Math.round(data.marine.wave_direction_deg)}° ${windCompass(data.marine.wave_direction_deg)}`
                  : 'Direction —'
              }
            />
            <StatCard accent="cyan" label="Wave period" value={fmt(data?.marine.wave_period_s, 1, ' s')} />
            <StatCard
              accent="violet"
              label="Swell height"
              value={fmt(data?.marine.swell_height_m, 2, ' m')}
              sub={
                data?.marine.swell_direction_deg != null
                  ? `${Math.round(data.marine.swell_direction_deg)}° ${windCompass(data.marine.swell_direction_deg)}`
                  : undefined
              }
            />
            <StatCard
              accent="amber"
              label="Swell period"
              value={fmt(data?.marine.swell_period_s, 1, ' s')}
            />
            <StatCard accent="emerald" label="Wind waves" value={fmt(data?.marine.wind_wave_height_m, 2, ' m')} />
            <StatCard accent="rose" label="Sea surface" value={fmt(data?.marine.sea_surface_temp_c, 1, ' °C')} />
            <StatCard
              accent="sky"
              label="Wind (10 m)"
              value={fmt(data?.weather.wind_speed_kmh, 0, ' km/h')}
              sub={
                data?.weather.wind_direction_deg != null
                  ? `${Math.round(data.weather.wind_direction_deg)}° ${windCompass(data.weather.wind_direction_deg)}`
                  : undefined
              }
            />
            <StatCard
              accent="violet"
              label="Sky / conditions"
              value={wxLine ?? '—'}
              sub={dayNight ? dayNight : undefined}
            />
          </div>
        )}

        <p className="mt-4 text-[11px] leading-relaxed text-slate-400">
          {data?.attribution ??
            'Data: Open-Meteo (free API). For demonstration; verify with your local marine weather authority.'}
        </p>
        {data?.fetched_at && (
          <p className="mt-1 text-[11px] text-slate-500">
            Updated {new Date(data.fetched_at).toLocaleString()}
          </p>
        )}
      </div>
    </section>
  )
}
