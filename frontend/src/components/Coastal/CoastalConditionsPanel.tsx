import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { apiService } from '../../services/api'
import type { CoastalConditionsResponse } from '../../types/coastal'

function fmt(n: number | null | undefined, digits = 1, suffix = ''): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return `${n.toFixed(digits)}${suffix}`
}

export default function CoastalConditionsPanel() {
  const [data, setData] = useState<CoastalConditionsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await apiService.getCoastalConditions())
    } catch (cause) {
      setData(null)
      if (axios.isAxiosError(cause) && !cause.response) {
        setError('Marine conditions appear when the API is awake.')
      } else {
        setError('Marine conditions are unavailable right now.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 15 * 60 * 1000)
    return () => window.clearInterval(id)
  }, [load])

  return (
    <section className="panel panel-pad" aria-label="Live coastal conditions">
      <div className="row" style={{ marginBottom: 12 }}>
        <div>
          <p className="kicker">Environment</p>
          <h3>{data?.location.label ?? 'Patrol conditions'}</h3>
        </div>
        <button type="button" className="btn-ghost" onClick={() => void load()} disabled={loading}>
          {loading ? 'Loading' : 'Refresh'}
        </button>
      </div>
      {error && !data ? <p className="meta">{error}</p> : null}
      {loading && !data ? <p className="meta">Loading waves, swell, and wind.</p> : null}
      {data ? (
        <div className="coastal">
          <div><span>Wave</span><b>{fmt(data.marine.wave_height_m, 1, ' m')}</b></div>
          <div><span>Period</span><b>{fmt(data.marine.wave_period_s, 0, ' s')}</b></div>
          <div><span>Swell</span><b>{fmt(data.marine.swell_height_m, 1, ' m')}</b></div>
          <div><span>Wind</span><b>{fmt(data.weather.wind_speed_kmh, 0, ' km/h')}</b></div>
          <div><span>Sea</span><b>{fmt(data.marine.sea_surface_temp_c, 1, '°')}</b></div>
          <div><span>Source</span><b style={{ fontSize: 13 }}>Open-Meteo</b></div>
        </div>
      ) : null}
    </section>
  )
}
