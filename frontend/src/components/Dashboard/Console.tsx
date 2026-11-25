import { useEffect, useState } from 'react'
import type { ConnectionState } from '../../hooks/useWebSocket'
import type { AlertData, FrameResult } from '../../types/frameResult'
import type { Swimmer } from '../../types/swimmer'
import type { PatrolState } from '../../utils/patrolRisk'
import CoastalConditionsPanel from '../Coastal/CoastalConditionsPanel'
import FocusMode from '../Lifeguard/FocusMode'
import VideoPlayer from '../VideoFeed/VideoPlayer'
import VideoUploader from '../VideoUpload/VideoUploader'

const GITHUB = 'https://github.com/bardan8586/Beach-Assistant'

const STATUS_COPY: Record<PatrolState, { title: string; detail: string }> = {
  idle: { title: 'Standby', detail: 'No clip is loaded. Upload patrol footage to start scoring risk.' },
  clear: { title: 'Clear', detail: 'No open watch, alert, or emergency. Keep looking at the water.' },
  watch: { title: 'Watch', detail: 'A track needs a closer look. It is not an emergency yet.' },
  alert: { title: 'Alert', detail: 'A priority alert is open. Acknowledge it or focus the track.' },
  emergency: { title: 'Emergency', detail: 'An unacknowledged emergency is open. This is a prompt to look, not a rescue order.' },
  analyzing: { title: 'Analyzing', detail: 'The model is reading the clip. Counts appear with the first frames.' },
  waking: { title: 'Waking', detail: 'The free API host sleeps when idle. The first request can take up to a minute.' },
  offline: { title: 'Offline', detail: 'The dashboard cannot reach the API. Check VITE_API_URL, or wait if the host is still starting.' },
}

const CLASSES = [
  { id: 'swimming', label: 'Swimming' },
  { id: 'drowning', label: 'Drowning' },
  { id: 'out_of_water', label: 'Out of water' },
  { id: 'person', label: 'Person' },
] as const

export type ApiPhase = 'checking' | 'online' | 'waking' | 'offline'

interface ConsoleProps {
  apiPhase: ApiPhase
  connectionState: ConnectionState
  patrol: PatrolState
  swimmers: Swimmer[]
  alerts: AlertData[]
  timeline: AlertData[]
  frameCount: number
  selectedCamera: string
  uploadedVideo: File | null
  videoUrl: string
  frameResults: FrameResult[]
  processing: boolean
  processingStatus: string
  uploadProgress: number
  playbackMode: boolean
  playbackError: string | null
  audioEnabled: boolean
  autoAnalyze: boolean
  openCvWindow: boolean
  maxUploadBytes: number | null
  showBoundingBoxes: boolean
  showHeatmap: boolean
  showZones: boolean
  focusedSwimmer: Swimmer | null
  onVideoFile: (file: File) => void
  onReject: (message: string) => void
  onReset: () => void
  onStart: () => void
  onLoadPlayback: () => void
  onExitPlayback: () => void
  onDismissError: () => void
  onAcknowledge: (id: string) => void
  onFocus: (id: number) => void
  onExitFocus: () => void
  onToggleAudio: () => void
  onToggleBoxes: () => void
  onToggleHeatmap: () => void
  onToggleZones: () => void
  onAutoAnalyze: (value: boolean) => void
  onOpenCv: (value: boolean) => void
}

function classKey(value?: string): (typeof CLASSES)[number]['id'] {
  const key = (value || 'person').toLowerCase().replace(/\s+/g, '_')
  if (key === 'swimming' || key === 'drowning' || key === 'out_of_water' || key === 'person') return key
  if (key.includes('drown')) return 'drowning'
  if (key.includes('swim')) return 'swimming'
  if (key.includes('water') || key.includes('land')) return 'out_of_water'
  return 'person'
}

function riskTone(level?: string, score?: number): 'high' | 'medium' | 'low' {
  const normalized = (level || '').toLowerCase()
  if (normalized === 'high' || normalized === 'critical' || (score ?? 0) >= 70) return 'high'
  if (normalized === 'medium' || (score ?? 0) >= 40) return 'medium'
  return 'low'
}

export default function Console(props: ConsoleProps) {
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    document.documentElement.dataset.theme === 'light' ? 'light' : 'dark',
  )
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('ba-theme', theme)
  }, [theme])

  const counts = { swimming: 0, drowning: 0, out_of_water: 0, person: 0 }
  for (const swimmer of props.swimmers) counts[classKey(swimmer.detection_class)] += 1
  const copy = STATUS_COPY[props.patrol]
  const feedLabel =
    props.connectionState === 'connected' ? 'Feed live'
      : props.connectionState === 'connecting' || props.connectionState === 'reconnecting' ? 'Feed reconnecting'
        : 'Feed idle'
  const apiLabel =
    props.apiPhase === 'online' ? 'API online'
      : props.apiPhase === 'checking' ? 'API checking'
        : props.apiPhase === 'waking' ? 'API waking'
          : 'API offline'

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="mark" aria-hidden>BA</div>
          <div>
            <h1>Beach Assistant</h1>
            <p>Computer vision for early beach-risk signals. A second set of eyes, not a lifeguard.</p>
          </div>
        </div>
        <div className="top-actions">
          <span className="chip" data-on={props.connectionState === 'connected' ? 'true' : props.connectionState === 'reconnecting' ? 'waking' : 'false'}>
            <i /> {feedLabel}
          </span>
          <span className="chip" data-on={props.apiPhase === 'online' ? 'true' : props.apiPhase === 'waking' || props.apiPhase === 'checking' ? 'waking' : 'false'}>
            <i /> {apiLabel}
          </span>
          <button type="button" className="btn-ghost" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          <a className="btn-ghost" href={GITHUB} target="_blank" rel="noreferrer">GitHub</a>
        </div>
      </header>

      <main className="page">
        <section className="intro">
          <div>
            <p className="kicker">Patrol console</p>
            <h2>See the water, the counts, and the risk in one view.</h2>
            <p className="lede">
              Upload a surf club clip. The model marks people, keeps track IDs, and raises a single patrol state from standby to emergency.
            </p>
          </div>
          <p className="mono meta">{props.selectedCamera} · {props.frameCount} frames</p>
        </section>

        {(props.apiPhase === 'waking' || props.apiPhase === 'checking') && (
          <div className="notice" role="status">
            <strong>{props.apiPhase === 'checking' ? 'Checking the API' : 'Waking the server'}</strong>
            The free host sleeps when nobody is using it. The first request can take up to a minute. This page will fill in on its own.
          </div>
        )}

        <section className="status-row" aria-label="Patrol status and class counts">
          <div className="patrol" data-state={props.patrol} role="status" aria-live="polite">
            <div>
              <p className="kicker" style={{ color: 'inherit', opacity: 0.7 }}>Patrol status</p>
              <strong>{copy.title}</strong>
              <p>{copy.detail}</p>
            </div>
          </div>
          <div className="panel panel-pad">
            <div className="row" style={{ marginBottom: 12 }}>
              <h3>Live counts</h3>
              <span className="meta">{props.swimmers.length} tracks</span>
            </div>
            <div className="counts">
              {CLASSES.map((item) => (
                <div className="count" data-hot={counts[item.id] > 0 ? item.id : undefined} key={item.id}>
                  <span>{item.label}</span>
                  <b>{counts[item.id]}</b>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="workspace">
          <div className="panel panel-pad" style={{ display: 'grid', gap: 14 }}>
            <div className="stage-head">
              <div>
                <p className="kicker">Camera</p>
                <h3>{props.uploadedVideo ? props.uploadedVideo.name : 'No patrol video loaded'}</h3>
              </div>
              <div className="top-actions">
                <button type="button" className="btn-ghost" data-on={props.showBoundingBoxes ? 'true' : 'false'} onClick={props.onToggleBoxes}>Boxes</button>
                <button type="button" className="btn-ghost" data-on={props.showZones ? 'true' : 'false'} onClick={props.onToggleZones}>Zones</button>
                <button type="button" className="btn-ghost" data-on={props.showHeatmap ? 'true' : 'false'} onClick={props.onToggleHeatmap}>Heat</button>
                <button type="button" className="btn-ghost" onClick={props.onToggleAudio}>{props.audioEnabled ? 'Sound on' : 'Muted'}</button>
                {props.uploadedVideo && (
                  <button type="button" className="btn-ghost" onClick={props.onReset} disabled={props.processing || props.processingStatus === 'uploading'}>New clip</button>
                )}
              </div>
            </div>

            {props.playbackError && (
              <div className="banner-error" role="alert">
                <div className="row">
                  <span>{props.playbackError}</span>
                  <button type="button" className="btn-ghost" onClick={props.onDismissError}>Dismiss</button>
                </div>
              </div>
            )}

            {!props.uploadedVideo ? (
              <VideoUploader
                onVideoSelected={props.onVideoFile}
                onReject={props.onReject}
                uploadProgress={props.uploadProgress}
                stage={props.processingStatus === 'uploading' ? 'uploading' : 'idle'}
                maxUploadBytes={props.maxUploadBytes}
                statusMessage={props.processingStatus === 'uploading' ? `Uploading ${props.uploadProgress}%` : undefined}
              />
            ) : (
              <VideoPlayer
                frameResults={props.frameResults}
                showBoundingBoxes={props.showBoundingBoxes}
                showHeatmap={props.showHeatmap}
                showZones={props.showZones}
                cameraId={props.selectedCamera}
                videoUrl={props.videoUrl}
                isLive={props.processing}
              />
            )}

            {props.processingStatus === 'uploading' && (
              <div>
                <div className="row" style={{ marginBottom: 6 }}>
                  <span className="meta">Uploading</span>
                  <span className="mono">{props.uploadProgress}%</span>
                </div>
                <div className="progress" role="progressbar" aria-valuenow={props.uploadProgress} aria-valuemin={0} aria-valuemax={100}>
                  <span style={{ width: `${Math.max(props.uploadProgress, 4)}%` }} />
                </div>
              </div>
            )}

            {props.processing && (
              <p className="meta" role="status">
                {props.frameResults.length > 0
                  ? `${props.frameResults.length} frames in · ${props.swimmers.length} tracks`
                  : 'Pipeline is warming up. The first frames can take a little while on a cold server.'}
              </p>
            )}

            <div className="row">
              <label className="meta" style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                <input type="checkbox" checked={props.autoAnalyze} onChange={(event) => props.onAutoAnalyze(event.target.checked)} />
                Analyze after upload
              </label>
              <label className="meta" style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                <input type="checkbox" checked={props.openCvWindow} onChange={(event) => props.onOpenCv(event.target.checked)} disabled={props.processing} />
                OpenCV window on the API machine
              </label>
              {props.uploadedVideo && !props.processing && props.processingStatus !== 'uploading' && (
                <button type="button" className="btn" onClick={props.onStart}>
                  {props.processingStatus === 'idle' ? 'Run analysis' : 'Run again'}
                </button>
              )}
              {props.playbackMode && (
                <button type="button" className="btn-ghost" onClick={props.onExitPlayback}>Exit playback</button>
              )}
              {!props.playbackMode && !props.processing && props.processingStatus === 'completed' && (
                <button type="button" className="btn-ghost" onClick={props.onLoadPlayback}>Load saved results</button>
              )}
            </div>
          </div>

          <div style={{ display: 'grid', gap: 16 }}>
            <section className="panel panel-pad" aria-label="Alert timeline">
              <div className="row" style={{ marginBottom: 12 }}>
                <h3>Event timeline</h3>
                <span className="meta">{props.timeline.filter((item) => !item.acknowledged).length} open</span>
              </div>
              {props.timeline.length === 0 ? (
                <p className="meta">No events yet. Watches, alerts, and emergencies land here in order.</p>
              ) : (
                <div className="timeline">
                  {props.timeline.map((alert) => (
                    <article className="event" data-level={alert.level} key={alert.alert_id}>
                      <div className="bar" aria-hidden />
                      <div>
                        <b>{alert.level} · track {alert.swimmer_id}</b>
                        <p>{alert.action_recommended}</p>
                        <p className="mono">{alert.zone} · score {Math.round(alert.risk_score)}{alert.acknowledged ? ' · acknowledged' : ''}</p>
                      </div>
                      {!alert.acknowledged && (
                        <button type="button" className="btn-ghost" onClick={() => props.onAcknowledge(alert.alert_id)}>Ack</button>
                      )}
                    </article>
                  ))}
                </div>
              )}
              {props.timeline.some((alert) => !alert.acknowledged) && (
                <div className="row" style={{ marginTop: 10 }}>
                  <span className="meta">Focus opens the track on the video.</span>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => {
                      const next = props.timeline.find((alert) => !alert.acknowledged)
                      if (next) props.onFocus(next.swimmer_id)
                    }}
                  >
                    Focus top event
                  </button>
                </div>
              )}
            </section>
            <CoastalConditionsPanel />
          </div>
        </section>

        <section className="panel" aria-label="Active tracks">
          <div className="panel-pad row" style={{ borderBottom: '1px solid var(--line)' }}>
            <h3>Tracks</h3>
            <span className="meta">{props.swimmers.length === 0 ? 'Empty until the pipeline publishes a frame' : `${props.swimmers.length} active`}</span>
          </div>
          {props.swimmers.length === 0 ? (
            <p className="meta" style={{ padding: 16 }}>No active tracks. Run a clip or wait for the live feed.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="tracks">
                <thead>
                  <tr>
                    <th>Track</th>
                    <th>Class</th>
                    <th>Risk</th>
                    <th>Zone</th>
                    <th>Confidence</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {props.swimmers.map((swimmer) => (
                    <tr key={swimmer.track_id}>
                      <td className="mono">{swimmer.track_id}</td>
                      <td style={{ textTransform: 'capitalize' }}>{(swimmer.detection_class || 'person').replaceAll('_', ' ')}</td>
                      <td>
                        <span className={`pill ${riskTone(swimmer.risk_level, swimmer.risk_score)}`}>
                          {swimmer.risk_score != null ? Math.round(swimmer.risk_score) : '—'} {swimmer.risk_level || ''}
                        </span>
                      </td>
                      <td>{swimmer.zone || '—'}</td>
                      <td className="mono">{((swimmer.confidence ?? 0) * 100).toFixed(0)}%</td>
                      <td><button type="button" className="btn-ghost" onClick={() => props.onFocus(swimmer.track_id)}>Focus</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      {props.focusedSwimmer && (
        <FocusMode swimmer={props.focusedSwimmer} onExit={props.onExitFocus} />
      )}
    </div>
  )
}
