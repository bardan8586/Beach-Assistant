import { useEffect, useState } from 'react'
import type { Swimmer } from '../../types/swimmer'

interface FocusModeProps {
  swimmer: Swimmer | null
  onExit: () => void
  videoRef?: HTMLVideoElement | null
}

export default function FocusMode({ swimmer, onExit, videoRef }: FocusModeProps) {
  const [riskHistory, setRiskHistory] = useState<number[]>([])
  const riskScore = swimmer?.risk_score ?? 0

  useEffect(() => {
    if (!swimmer) return
    setRiskHistory((prev) => [...prev.slice(-60), riskScore])
  }, [swimmer, riskScore])

  if (!swimmer) return null

  return (
    <div className="focus-scrim" role="dialog" aria-modal="true" aria-label={`Track ${swimmer.track_id}`}>
      <div className="row" style={{ marginBottom: 20 }}>
        <div>
          <p className="kicker">Focused track</p>
          <h2 style={{ margin: 0, letterSpacing: '-0.03em' }}>Track {swimmer.track_id}</h2>
        </div>
        <button type="button" className="btn" onClick={onExit}>Close</button>
      </div>
      <div className="workspace">
        <section className="panel panel-pad">
          <p className="kicker">Risk</p>
          <p style={{ margin: '8px 0 0', fontSize: 64, letterSpacing: '-0.05em', lineHeight: 1 }}>{Math.round(riskScore)}</p>
          <p className="meta">{swimmer.risk_level || 'Unscored'} · {swimmer.zone || 'zone unknown'}</p>
          <div className="coastal" style={{ marginTop: 16 }}>
            <div><span>Class</span><b style={{ fontSize: 14, textTransform: 'capitalize' }}>{(swimmer.detection_class || 'person').replaceAll('_', ' ')}</b></div>
            <div><span>Behavior</span><b style={{ fontSize: 14 }}>{swimmer.behavior || '—'}</b></div>
            <div><span>In water</span><b style={{ fontSize: 14 }}>{Math.round(swimmer.time_in_water ?? 0)}s</b></div>
            <div><span>Confidence</span><b style={{ fontSize: 14 }}>{((swimmer.confidence ?? 0) * 100).toFixed(0)}%</b></div>
          </div>
          <div style={{ marginTop: 18 }}>
            <p className="kicker">Recent scores</p>
            <div style={{ display: 'flex', alignItems: 'end', gap: 3, height: 72, marginTop: 8 }}>
              {riskHistory.map((risk, index) => (
                <div
                  key={`${index}-${risk}`}
                  style={{
                    flex: 1,
                    height: `${Math.max(4, risk)}%`,
                    background: risk >= 70 ? 'var(--emergency)' : risk >= 40 ? 'var(--watch)' : 'var(--clear)',
                    borderRadius: 3,
                  }}
                />
              ))}
            </div>
          </div>
        </section>
        <section className="panel panel-pad">
          <p className="kicker">Position</p>
          <p className="mono" style={{ marginTop: 8 }}>
            {swimmer.bbox?.x ?? swimmer.bbox?.x1 ?? 0}, {swimmer.bbox?.y ?? swimmer.bbox?.y1 ?? 0}
          </p>
          <p className="meta" style={{ marginTop: 12 }}>
            {videoRef
              ? 'The main player stays in sync behind this panel.'
              : 'Return to the console to watch this track on the clip.'}
          </p>
        </section>
      </div>
    </div>
  )
}
