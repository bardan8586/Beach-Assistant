/**
 * Main App Component - Complete Video Processing Dashboard
 * ========================================================
 * Full workflow: Upload video -> Process with AI -> Real-time tracking display
 */

import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import './index.css'

// Components
import Header from './components/Layout/Header'
import SectionHeader from './components/Layout/SectionHeader'
import DetailedStats from './components/Stats/DetailedStats'
import VideoPlayer from './components/VideoFeed/VideoPlayer'
import SwimmerList from './components/Swimmers/SwimmerList'
import PriorityDashboard from './components/Lifeguard/PriorityDashboard'
import FocusMode from './components/Lifeguard/FocusMode'
import VideoUploader from './components/VideoUpload/VideoUploader'
import VideoCommandStrip from './components/VideoUpload/VideoCommandStrip'
import DataDebugPanel from './components/Debug/DataDebugPanel'
import CoastalConditionsPanel from './components/Coastal/CoastalConditionsPanel'
import { useAppStore } from './store/useAppStore'
import { useWebSocket } from './hooks/useWebSocket'
import { apiService } from './services/api'
import { videoService } from './services/videoService'
import { playbackService } from './services/playbackService'
import { audioAlertService } from './services/audioAlertService'
import type { FrameResult, AlertData } from './types/frameResult'

function App() {
  const [uploadedVideo, setUploadedVideo] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string>('')
  const [videoId, setVideoId] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [processingStatus, setProcessingStatus] = useState<string>('idle')
  const [openCvWindow, setOpenCvWindow] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const [maxUploadBytes, setMaxUploadBytes] = useState<number | null>(null)

  // FrameResult data for playback mode
  const [frameResults, setFrameResults] = useState<FrameResult[]>([])
  const [playbackMode, setPlaybackMode] = useState(false)  // true = playback, false = live
  
  // Alert management
  const [alerts, setAlerts] = useState<AlertData[]>([])
  const [audioEnabled, setAudioEnabled] = useState(true)
  
  // Focus mode
  const [focusedSwimmerId, setFocusedSwimmerId] = useState<number | null>(null)

  // User-visible errors (e.g. playback load failed)
  const [playbackError, setPlaybackError] = useState<string | null>(null)

  const statusPollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  // Get data from store
  const { 
    swimmers, 
    showBoundingBoxes, 
    showHeatmap, 
    showZones,
    selectedCamera,
    updateSwimmers,
    setIsConnected,
    toggleBoundingBoxes,
    toggleHeatmap,
    toggleZones,
    setSelectedCamera
  } = useAppStore()

  // Connect WebSocket for real-time updates
  const { isConnected: wsConnected } = useWebSocket({
    cameraId: selectedCamera,
    onMessage: (message) => {
      // Backend sends { type: "frame_result", camera_id, data: FrameResult } — unwrap and use .data
      const fr = (message as { type?: string; data?: FrameResult }).type === 'frame_result' && (message as { data?: FrameResult }).data
        ? (message as { data: FrameResult }).data
        : (message as unknown as FrameResult)

      const swimmers = fr?.swimmers ?? (message as { swimmers?: FrameResult['swimmers'] }).swimmers
      const alertsList = fr?.alerts ?? (message as { alerts?: FrameResult['alerts'] }).alerts
      const isFrameResult = fr && typeof fr.frame_index === 'number' && typeof fr.video_width === 'number'

      if (isFrameResult || swimmers || alertsList) {
        const cam = (fr?.camera_id ?? (message as { camera_id?: string }).camera_id) || selectedCamera

        if (alertsList && Array.isArray(alertsList)) {
          setAlerts(alertsList)
          alertsList.forEach((alert: { alert_id: string; level: string; swimmer_id: number; zone: string; action_recommended: string; acknowledged?: boolean }) => {
            if (!alert.acknowledged && (alert.level === 'emergency' || alert.level === 'alert')) {
              audioAlertService.speakAlert(alert.swimmer_id, alert.level, alert.zone, alert.action_recommended, alert.alert_id)
            }
          })
        }

        if (swimmers && Array.isArray(swimmers)) {
          const formattedSwimmers = swimmers.map((s: { track_id: number; bbox?: { x: number; y: number; w: number; h: number }; confidence?: number; risk_score?: number; risk_level?: string; behavior?: string; zone?: string; time_in_water?: number; velocity?: number }) => ({
            track_id: s.track_id,
            camera_id: cam,
            bbox: s.bbox || { x: 0, y: 0, w: 0, h: 0 },
            confidence: s.confidence ?? 0.8,
            risk_score: s.risk_score ?? 0,
            risk_level: s.risk_level ?? 'LOW',
            behavior: s.behavior ?? 'NORMAL',
            zone: s.zone ?? 'SAFE',
            time_in_water: s.time_in_water ?? 0,
            velocity: s.velocity ?? 0,
            first_seen: new Date().toISOString(),
            last_seen: new Date().toISOString(),
            status: 'active' as const
          }))
          updateSwimmers(formattedSwimmers)
        }

        // Push frame into frameResults so VideoPlayer can draw overlays (OpenCV-style view)
        if (isFrameResult && fr) {
          const frame: FrameResult = {
            video_id: fr.video_id ?? 'realtime',
            camera_id: cam,
            frame_index: fr.frame_index,
            timestamp_ms: fr.timestamp_ms ?? 0,
            video_width: fr.video_width,
            video_height: fr.video_height,
            swimmers: fr.swimmers ?? [],
            scene: fr.scene,
            metrics: fr.metrics,
            alerts: fr.alerts ?? [],
            system_mode: fr.system_mode ?? 'live'
          }
          setFrameResults(prev => {
            const idx = prev.findIndex(f => f.frame_index === frame.frame_index)
            const next = idx >= 0
              ? prev.map((f, i) => (i === idx ? frame : f))
              : [...prev, frame].sort((a, b) => a.frame_index - b.frame_index)
            return next.length > 600 ? next.slice(-600) : next
          })
        }
      } else if ((message as { type?: string }).type === 'swimmers' && (message as { data?: unknown }).data && Array.isArray((message as { data: unknown[] }).data)) {
        const data = (message as { data: Array<{ track_id: number; bbox?: unknown; first_seen?: string; last_seen?: string; confidence?: number }> }).data
        if ((message as { camera_id?: string }).camera_id === selectedCamera || (message as { camera_id?: string }).camera_id === 'all') {
          const formattedSwimmers = data.map((s) => ({
            track_id: s.track_id,
            camera_id: (message as { camera_id: string }).camera_id ?? selectedCamera,
            bbox: s.bbox || { x1: 0, y1: 0, x2: 0, y2: 0 },
            confidence: s.confidence ?? 0.8,
            first_seen: s.first_seen ?? new Date().toISOString(),
            last_seen: s.last_seen ?? new Date().toISOString(),
            status: 'active' as const
          }))
          updateSwimmers(formattedSwimmers)
        }
      }
    },
    autoConnect: true
  })

  // Update connection status
  useEffect(() => {
    setIsConnected(wsConnected)
  }, [wsConnected, setIsConnected])

  useEffect(() => {
    void apiService
      .getVideoUploadLimits()
      .then((lim) => setMaxUploadBytes(lim.max_upload_bytes))
      .catch(() => setMaxUploadBytes(50 * 1024 * 1024))
  }, [])

  // Fetch initial data and refresh
  useEffect(() => {
    const fetchData = async () => {
      try {
        const swimmersData = await apiService.getSwimmers(selectedCamera)
        if (swimmersData.length > 0) {
          console.log(`📊 Fetched ${swimmersData.length} swimmers from API`)
          updateSwimmers(swimmersData)
        }
      } catch (error) {
        console.error('Failed to fetch initial swimmers:', error)
      }
    }
    fetchData()
    // Refresh every 3 seconds as fallback
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [selectedCamera, updateSwimmers])

  // Handle video file selection — upload, then auto-trigger AI processing (smooth flow).
  const handleVideoSelected = async (file: File) => {
    setPlaybackError(null)
    if (maxUploadBytes != null && file.size > maxUploadBytes) {
      const mb = Math.max(1, Math.round(maxUploadBytes / (1024 * 1024)))
      setPlaybackError(`Video too large (max ${mb} MB). Trim the clip or lower resolution and try again.`)
      return
    }

    setUploadedVideo(file)
    setFrameResults([])
    setPlaybackMode(false)
    setUploadProgress(0)

    const url = URL.createObjectURL(file)
    setVideoUrl(url)

    try {
      setProcessingStatus('uploading')
      const uploadResult = await videoService.uploadVideo(file, (pct) => setUploadProgress(pct))
      setVideoId(uploadResult.video_id)

      const cameraId = `upload_${uploadResult.video_id.substring(0, 8)}`
      setSelectedCamera(cameraId)
      setProcessingStatus('idle')

      // Auto-analyze for a smooth, single-click experience (user can opt out).
      if (autoAnalyze) {
        // Small delay so WebSocket reconnects to the new camera_id before frames arrive.
        setTimeout(() => handleStartProcessing(uploadResult.video_id, cameraId), 400)
      }
    } catch (error) {
      console.error('Error uploading video:', error)
      setProcessingStatus('error')
      if (axios.isAxiosError(error)) {
        const ax = error
        const d = ax.response?.data?.detail
        if (ax.response?.status === 413 && d && typeof d === 'object' && d !== null && 'max_mb' in d) {
          setPlaybackError(`Video too large (server max ${(d as { max_mb: number }).max_mb} MB).`)
        } else {
          setPlaybackError('Upload failed. Check backend is running and try again.')
        }
      } else {
        setPlaybackError('Upload failed. Check backend is running and try again.')
      }
    }
  }

  // Start AI processing (auto-triggered after upload, or manually via button).
  const handleStartProcessing = async (overrideVideoId?: string, overrideCameraId?: string) => {
    const vid = overrideVideoId ?? videoId
    if (!vid) return
    if (statusPollRef.current) {
      clearInterval(statusPollRef.current)
      statusPollRef.current = null
    }
    setPlaybackError(null)
    setPlaybackMode(false)
    setFrameResults([])
    setProcessingStatus('processing')
    setProcessing(true)

    const cameraId = overrideCameraId || selectedCamera || `upload_${vid.substring(0, 8)}`
    try {
      await new Promise(resolve => setTimeout(resolve, 300))  // Let WebSocket reconnect if needed
      const processResult = await videoService.processVideo(vid, {
        camera_id: cameraId,
        show_window: openCvWindow
      })
      console.log('🚀 AI processing started:', processResult)

      statusPollRef.current = setInterval(async () => {
        try {
          const status = await videoService.getStatus(vid)
          if (status.status === 'completed') {
            if (statusPollRef.current) {
              clearInterval(statusPollRef.current)
              statusPollRef.current = null
            }
            setProcessingStatus('completed')
            setProcessing(false)
            setPlaybackError(null)
            if (status.return_code !== undefined && status.return_code !== 0) {
              setPlaybackError(
                `Processing failed (exit code ${status.return_code}). Check backend logs. If you see "No module named 'torch'" or "ultralytics", run: cd ai && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
              )
            } else {
              try {
                const results = await playbackService.loadFrameResults(vid)
                setFrameResults(results)
                setPlaybackMode(true)
              } catch {
                setPlaybackError('Processing finished but results could not be loaded. Use "Load results" to retry.')
              }
            }
          }
        } catch (error) {
          console.error('Status check error:', error)
        }
      }, 2000)
    } catch (error) {
      console.error('Error starting processing:', error)
      setProcessingStatus('error')
      setProcessing(false)
      setPlaybackError('Failed to start AI processing. Check backend is running and see browser console.')
    }
  }
  
  // Reset upload state so user can analyze a new video
  const handleResetUpload = () => {
    if (statusPollRef.current) {
      clearInterval(statusPollRef.current)
      statusPollRef.current = null
    }
    if (videoUrl) URL.revokeObjectURL(videoUrl)
    setUploadedVideo(null)
    setVideoUrl('')
    setVideoId(null)
    setFrameResults([])
    setPlaybackMode(false)
    setProcessing(false)
    setProcessingStatus('idle')
    setUploadProgress(0)
    setPlaybackError(null)
    setAlerts([])
  }

  // Manual playback mode toggle
  const loadPlaybackData = async () => {
    if (!videoId) return
    setPlaybackError(null)
    try {
      const results = await playbackService.loadFrameResults(videoId)
      setFrameResults(results)
      setPlaybackMode(true)
    } catch {
      setPlaybackError('Analysis results not available yet. Run processing first, then try "Load results".')
    }
  }

  // Cleanup video URL
  useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl)
      }
    }
  }, [videoUrl])

  useEffect(() => {
    return () => {
      if (statusPollRef.current) {
        clearInterval(statusPollRef.current)
        statusPollRef.current = null
      }
    }
  }, [])
  
  // Alert handlers
  const handleAcknowledgeAlert = async (alertId: string) => {
    // Update local state immediately
    setAlerts(prev => prev.map(a => 
      a.alert_id === alertId ? { ...a, acknowledged: true } : a
    ))
    
    // TODO: Send acknowledgment to backend
    console.log(`✓ Alert ${alertId} acknowledged`)
  }
  
  const handleFocusSwimmer = (swimmerId: number) => {
    setFocusedSwimmerId(swimmerId)
  }
  
  const handleExitFocus = () => {
    setFocusedSwimmerId(null)
  }
  
  // Toggle audio
  const toggleAudio = () => {
    const newState = !audioEnabled
    setAudioEnabled(newState)
    audioAlertService.setEnabled(newState)
  }
  
  // Get focused swimmer data
  const focusedSwimmer = focusedSwimmerId 
    ? swimmers.find(s => s.track_id === focusedSwimmerId) 
    : null

  return (
    <div className="app-bg min-h-screen text-slate-200 antialiased">
      <Header
        selectedCamera={selectedCamera}
        isConnected={wsConnected}
        processingStatus={processingStatus}
        frameCount={frameResults.length}
      />

      <VideoCommandStrip
        uploadedVideo={uploadedVideo}
        uploadProgress={uploadProgress}
        processingStatus={processingStatus}
        processing={processing}
        maxUploadBytes={maxUploadBytes}
        onVideoFile={handleVideoSelected}
        onResetUpload={handleResetUpload}
      />

      <main className="mx-auto max-w-[1680px] space-y-10 px-4 py-8 sm:px-8 sm:py-10">
        <section aria-label="Coastal conditions">
          <SectionHeader
            kicker="Environment"
            title="Marine & surface conditions"
            description="Live Open-Meteo context for the default patrol coordinates. Use alongside video intelligence."
          />
          <CoastalConditionsPanel />
        </section>

        <section aria-label="Statistics">
          <SectionHeader
            kicker="Situation"
            title="Tracking overview"
            description="Aggregates from the current feed — updates as detections arrive."
          />
          <DetailedStats swimmers={swimmers} />
        </section>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-10">
          <div className="space-y-8 lg:col-span-8">
            <section className="card card-elevated cc-enter overflow-hidden p-6 sm:p-7" aria-label={uploadedVideo ? 'Video analysis' : 'Upload video'}>
              <div className="mb-6 flex flex-wrap items-start justify-between gap-4 border-b border-slate-700/50 pb-5">
                <div>
                  <p className="card-title">Video operations</p>
                  <h2 className="card-title-lg mt-1">
                    {uploadedVideo ? 'Analysis workspace' : 'Upload patrol clip'}
                  </h2>
                </div>
                {uploadedVideo && (
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="inline-flex max-w-md flex-col gap-0.5 text-xs text-slate-400 sm:flex-row sm:items-center sm:gap-2">
                      <span className="inline-flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="h-4 w-4 shrink-0 accent-cyan-500"
                          checked={openCvWindow}
                          onChange={(e) => setOpenCvWindow(e.target.checked)}
                          disabled={processing}
                        />
                        <span className="font-medium text-slate-300">OpenCV window</span>
                      </span>
                      <span className="text-slate-500 sm:pl-0">
                        Shows on the machine running the backend (same clip as the web player).
                      </span>
                    </label>
                    {processing && (
                      <span className="status-pill border border-red-500/40 bg-red-950/50 text-red-100">
                        Live
                      </span>
                    )}
                    {playbackMode && (
                      <span className="status-pill border border-emerald-500/35 bg-emerald-950/40 text-emerald-100">
                        Playback
                      </span>
                    )}
                    <button
                      onClick={toggleBoundingBoxes}
                      className={`btn-toggle ${showBoundingBoxes ? 'btn-toggle-active bg-emerald-600 hover:bg-emerald-700' : 'btn-toggle-inactive'}`}
                    >
                      {showBoundingBoxes ? '✓ ' : ''}Boxes
                    </button>
                    <button
                      onClick={toggleZones}
                      className={`btn-toggle ${showZones ? 'btn-toggle-active' : 'btn-toggle-inactive'}`}
                    >
                      {showZones ? '✓ ' : ''}Zones
                    </button>
                    <button
                      onClick={toggleHeatmap}
                      className={`btn-toggle ${showHeatmap ? 'btn-toggle-active bg-violet-600 hover:bg-violet-700' : 'btn-toggle-inactive'}`}
                    >
                      {showHeatmap ? '✓ ' : ''}Heatmap
                    </button>
                    <button
                      type="button"
                      onClick={handleResetUpload}
                      disabled={processing || processingStatus === 'uploading'}
                      className="btn-secondary disabled:cursor-not-allowed disabled:opacity-45"
                      title="Clear clip and workspace"
                    >
                      New video
                    </button>
                  </div>
                )}
              </div>

              {!uploadedVideo ? (
                <div className="space-y-4">
                  {playbackError && (
                    <div
                      role="alert"
                      className="flex items-center justify-between gap-4 rounded-xl border border-amber-500/30 bg-amber-950/35 px-4 py-3 text-amber-100"
                    >
                      <span className="text-sm font-medium">{playbackError}</span>
                      <button
                        type="button"
                        onClick={() => setPlaybackError(null)}
                        className="shrink-0 rounded-lg px-2 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-900/50"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                  <VideoUploader
                    onVideoSelected={handleVideoSelected}
                    uploadProgress={uploadProgress}
                    stage={processingStatus === 'uploading' ? 'uploading' : 'idle'}
                    maxUploadBytes={maxUploadBytes}
                    statusMessage={
                      processingStatus === 'uploading'
                        ? `Uploading ${uploadProgress}%`
                        : undefined
                    }
                  />
                  <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-700/60 bg-slate-950/35 px-4 py-3.5">
                    <label className="inline-flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-blue-600"
                        checked={autoAnalyze}
                        onChange={(e) => setAutoAnalyze(e.target.checked)}
                      />
                      <span>
                        <span className="font-medium">Auto-analyze after upload</span>
                        <span className="ml-1 text-slate-500">Start pipeline after upload.</span>
                      </span>
                    </label>
                    <label className="inline-flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-blue-600"
                        checked={openCvWindow}
                        onChange={(e) => setOpenCvWindow(e.target.checked)}
                      />
                      <span>
                        <span className="font-medium">Also open OpenCV window</span>
                        <span className="ml-1 text-slate-500">Local OpenCV window (optional).</span>
                      </span>
                    </label>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {playbackError && (
                    <div
                      role="alert"
                      className="flex items-center justify-between gap-4 rounded-xl border border-amber-500/30 bg-amber-950/35 px-4 py-3 text-amber-100"
                    >
                      <span className="text-sm font-medium">{playbackError}</span>
                      <button
                        type="button"
                        onClick={() => setPlaybackError(null)}
                        className="shrink-0 rounded-lg px-2 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-900/50"
                        aria-label="Dismiss"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                  <VideoPlayer
                    frameResults={frameResults}
                    showBoundingBoxes={showBoundingBoxes}
                    showHeatmap={showHeatmap}
                    showZones={showZones}
                    cameraId={selectedCamera}
                    videoUrl={videoUrl}
                    isLive={processing}
                    onToggleBoxes={toggleBoundingBoxes}
                    onToggleHeatmap={toggleHeatmap}
                    onToggleZones={toggleZones}
                  />

                  {/* Start / re-run analysis (same uploaded file; OpenCV uses checkbox above) */}
                  {!processing &&
                    (processingStatus === 'idle' ||
                      processingStatus === 'completed' ||
                      processingStatus === 'error') && (
                    <button
                      type="button"
                      onClick={() => handleStartProcessing()}
                      className="btn-primary w-full py-3.5"
                    >
                      {processingStatus === 'idle' ? 'Run AI analysis' : 'Re-run AI analysis'}
                    </button>
                  )}

                  {/* Upload progress (visible during upload, before processing starts) */}
                  {processingStatus === 'uploading' && (
                    <div className="space-y-2 rounded-xl border border-sky-500/25 bg-sky-950/40 p-4">
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-sky-100">Uploading video…</div>
                        <div className="text-sm font-semibold tabular-nums text-sky-200">{uploadProgress}%</div>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all"
                          style={{ width: `${Math.max(3, uploadProgress)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Processing Status */}
                  {processing && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-3 rounded-xl border border-cyan-500/25 bg-slate-950/50 p-4">
                        <div className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="relative flex h-2 w-2">
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                              <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
                            </span>
                            <span className="font-medium text-cyan-100">Live · AI processing</span>
                          </div>
                          <div className="text-sm text-slate-400 tabular-nums">
                            {frameResults.length > 0
                              ? `${frameResults.length} frames processed · ${swimmers.length} swimmer${swimmers.length === 1 ? '' : 's'} tracked`
                              : 'Warming up the pipeline…'}
                          </div>
                        </div>
                      </div>
                      {frameResults.length === 0 && (
                        <p className="px-1 text-xs text-slate-500" role="status">
                          No frames yet. If this stays 30+ seconds: check backend terminal for &quot;Started AI processing&quot; and &quot;Ingested FrameResult&quot; or errors.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Playback Mode Indicator */}
                  {playbackMode && (
                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-500/25 bg-emerald-950/30 p-4">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-emerald-300/90">Playback</div>
                        <div className="mt-0.5 text-sm font-medium text-emerald-100">
                          {frameResults.length} frames · overlays synced to timeline
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setPlaybackMode(false)}
                        className="btn-secondary"
                      >
                        Exit playback
                      </button>
                    </div>
                  )}

                  {/* Load Playback Button */}
                  {!playbackMode && !processing && processingStatus === 'completed' && (
                    <button
                      type="button"
                      onClick={loadPlaybackData}
                      className="w-full rounded-xl border border-emerald-500/40 bg-emerald-600 py-3.5 text-sm font-semibold text-white shadow-md transition hover:bg-emerald-500"
                    >
                      Load saved results for replay
                    </button>
                  )}
                </div>
              )}
            </section>

            <SwimmerList swimmers={swimmers} />
          </div>

          <aside className="space-y-6 lg:col-span-4">
            <SectionHeader
              kicker="Response"
              title="Alerts & system"
              description="Priority queue and connection health for the active feed."
            />

            <div className="card card-elevated cc-enter flex items-center justify-between gap-4 p-4 sm:p-5">
              <div>
                <p className="card-title">Audio</p>
                <p className="mt-0.5 text-sm text-slate-400">Spoken alerts for high-severity events</p>
              </div>
              <button
                type="button"
                onClick={toggleAudio}
                className={`btn-toggle shrink-0 px-4 py-2 ${audioEnabled ? 'btn-toggle-active bg-emerald-600 hover:bg-emerald-700' : 'btn-toggle-inactive'}`}
              >
                {audioEnabled ? 'Sound on' : 'Muted'}
              </button>
            </div>

            <PriorityDashboard
              alerts={alerts}
              onAcknowledge={handleAcknowledgeAlert}
              onFocus={handleFocusSwimmer}
              audioEnabled={audioEnabled}
            />

            <section className="card card-elevated cc-enter p-5 sm:p-6" aria-label="System status">
              <p className="card-title">Connectivity</p>
              <h3 className="card-title-lg mt-1 mb-5">System status</h3>
              <dl className="space-y-3.5 text-sm">
                <div className="flex justify-between gap-3 border-b border-slate-700/50 pb-3">
                  <dt className="text-slate-400">Backend API</dt>
                  <dd className="font-semibold text-emerald-400">Online</dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-700/50 pb-3">
                  <dt className="text-slate-400">WebSocket</dt>
                  <dd className={`font-semibold ${wsConnected ? 'text-emerald-400' : 'text-red-400'}`}>
                    {wsConnected ? 'Connected' : 'Disconnected'}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-700/50 pb-3">
                  <dt className="text-slate-400">AI pipeline</dt>
                  <dd className={`font-semibold ${swimmers.length > 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {swimmers.length > 0 ? 'Active' : 'Waiting'}
                  </dd>
                </div>
                <div className="flex justify-between gap-3 border-b border-slate-700/50 pb-3">
                  <dt className="text-slate-400">Video</dt>
                  <dd className={`font-semibold ${
                    processingStatus === 'processing' ? 'text-sky-400' :
                    processingStatus === 'completed' ? 'text-emerald-400' : 'text-slate-400'
                  }`}>
                    {processingStatus === 'idle' ? 'No video' :
                     processingStatus === 'uploading' ? 'Uploading…' :
                     processingStatus === 'processing' ? 'Processing…' :
                     processingStatus === 'completed' ? 'Complete' :
                     processingStatus === 'error' ? 'Error' : 'Ready'}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-400">Data stream</dt>
                  <dd className={`font-semibold ${
                    frameResults.length > 0 ? 'text-emerald-400' : wsConnected ? 'text-amber-400' : 'text-slate-500'
                  }`} title={frameResults.length > 0 ? 'Frames received from backend' : wsConnected ? 'Connected, waiting for frames' : 'Not connected'}>
                    {frameResults.length > 0
                      ? `Receiving frames (${frameResults.length})`
                      : wsConnected
                        ? 'No frames yet'
                        : '—'}
                  </dd>
                </div>
              </dl>
            </section>
          </aside>
        </div>
      </main>

      {/* Debug Panel */}
      <DataDebugPanel swimmers={swimmers} isConnected={wsConnected} selectedCamera={selectedCamera} />
      
      {/* Focus Mode Overlay */}
      {focusedSwimmer && (
        <FocusMode 
          swimmer={focusedSwimmer} 
          onExit={handleExitFocus}
        />
      )}
    </div>
  )
}

export default App
