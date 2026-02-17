/**
 * Main App Component - Complete Video Processing Dashboard
 * ========================================================
 * Full workflow: Upload video -> Process with AI -> Real-time tracking display
 */

import { useEffect, useState } from 'react'
import './index.css'

// Components
import Header from './components/Layout/Header'
import DetailedStats from './components/Stats/DetailedStats'
import VideoPlayer from './components/VideoFeed/VideoPlayer'
import SwimmerList from './components/Swimmers/SwimmerList'
import PriorityDashboard from './components/Lifeguard/PriorityDashboard'
import FocusMode from './components/Lifeguard/FocusMode'
import VideoUploader from './components/VideoUpload/VideoUploader'
import DataDebugPanel from './components/Debug/DataDebugPanel'
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

  // Handle video file selection — upload only; user clicks "Start processing" to run AI
  const handleVideoSelected = async (file: File) => {
    setUploadedVideo(file)
    setFrameResults([])
    setPlaybackMode(false)
    setPlaybackError(null)

    const url = URL.createObjectURL(file)
    setVideoUrl(url)

    try {
      setProcessingStatus('uploading')
      const uploadResult = await videoService.uploadVideo(file)
      setVideoId(uploadResult.video_id)

      const cameraId = `upload_${uploadResult.video_id.substring(0, 8)}`
      setSelectedCamera(cameraId)
      setProcessingStatus('idle')  // Upload done; waiting for user to click "Start processing"
    } catch (error) {
      console.error('Error uploading video:', error)
      setProcessingStatus('error')
    }
  }

  // Start AI processing (called when user clicks "Start processing" button)
  const handleStartProcessing = async () => {
    if (!videoId) return
    setPlaybackError(null)
    setProcessingStatus('processing')
    setProcessing(true)

    const cameraId = selectedCamera || `upload_${videoId.substring(0, 8)}`
    try {
      await new Promise(resolve => setTimeout(resolve, 500))  // Let WebSocket reconnect if needed
      const processResult = await videoService.processVideo(videoId, {
        camera_id: cameraId,
        show_window: openCvWindow
      })
      console.log('🚀 AI processing started:', processResult)

      const statusInterval = setInterval(async () => {
        try {
          const status = await videoService.getStatus(videoId)
          if (status.status === 'completed') {
            clearInterval(statusInterval)
            setProcessingStatus('completed')
            setProcessing(false)
            setPlaybackError(null)
            if (status.return_code !== undefined && status.return_code !== 0) {
              setPlaybackError(
                `Processing failed (exit code ${status.return_code}). Check backend logs. If you see "No module named 'torch'" or "ultralytics", run: cd ai && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
              )
            } else {
              try {
                const results = await playbackService.loadFrameResults(videoId)
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
    <div className="min-h-screen" style={{ backgroundColor: 'rgb(var(--color-surface))' }}>
      <Header
        selectedCamera={selectedCamera}
        isConnected={wsConnected}
        processingStatus={processingStatus}
        frameCount={frameResults.length}
      />

      {/* Main Dashboard */}
      <main className="container mx-auto px-4 sm:px-6 py-6 max-w-[1600px]">
        {/* Top Stats Row */}
        <section className="mb-6" aria-label="Statistics">
          <DetailedStats swimmers={swimmers} />
        </section>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column: Video Section (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Video Upload or Player */}
            <section className="card p-5" aria-label={uploadedVideo ? 'Video analysis' : 'Upload video'}>
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <h2 className="card-title-lg flex items-center gap-2">
                  <span aria-hidden>📹</span>
                  {uploadedVideo ? 'Video Analysis' : 'Upload Video'}
                </h2>
                {uploadedVideo && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <label className="inline-flex items-center gap-2 text-xs text-slate-600">
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={openCvWindow}
                        onChange={(e) => setOpenCvWindow(e.target.checked)}
                        disabled={processing}
                      />
                      OpenCV window
                    </label>
                    {playbackMode && (
                      <span className="status-pill bg-emerald-100 text-emerald-800">
                        🎬 Playback
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
                  </div>
                )}
              </div>

              {!uploadedVideo ? (
                <VideoUploader onVideoSelected={handleVideoSelected} />
              ) : (
                <div className="space-y-4">
                  {playbackError && (
                    <div
                      role="alert"
                      className="flex items-center justify-between gap-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800"
                    >
                      <span className="text-sm font-medium">{playbackError}</span>
                      <button
                        type="button"
                        onClick={() => setPlaybackError(null)}
                        className="shrink-0 rounded px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100"
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
                    onToggleBoxes={toggleBoundingBoxes}
                    onToggleHeatmap={toggleHeatmap}
                    onToggleZones={toggleZones}
                  />

                  {/* Start processing — click this after upload to run AI; then use Play to watch with overlays */}
                  {!processing && processingStatus === 'idle' && (
                    <button
                      type="button"
                      onClick={handleStartProcessing}
                      className="w-full py-3 rounded-lg font-semibold bg-primary-600 text-white hover:bg-primary-700 transition-colors"
                      style={{ borderRadius: 'var(--radius-button)' }}
                    >
                      ▶ Start processing
                    </button>
                  )}

                  {/* Processing Status */}
                  {processing && (
                    <div className="space-y-2">
                      <div className="card flex items-center gap-3 p-4 border-l-4 border-l-blue-500 bg-blue-50/50">
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent" />
                        <div>
                          <div className="font-medium text-blue-900">AI Processing Active</div>
                          <div className="text-sm text-blue-700">Detecting swimmers and tracking in real-time…</div>
                        </div>
                      </div>
                      {frameResults.length === 0 && (
                        <p className="text-xs text-slate-500 px-1" role="status">
                          No frames yet. If this stays for 30+ seconds: check the backend terminal for &quot;Started AI processing&quot; and &quot;Ingested FrameResult&quot; or errors.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Playback Mode Indicator */}
                  {playbackMode && (
                    <div className="card flex flex-wrap items-center justify-between gap-3 p-4 border-l-4 border-l-emerald-500 bg-emerald-50/50">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl" aria-hidden>🎬</span>
                        <div>
                          <div className="font-medium text-emerald-900">Playback Mode</div>
                          <div className="text-sm text-emerald-700">
                            {frameResults.length} frames loaded · Overlays synced
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => setPlaybackMode(false)}
                        className="btn-toggle bg-white border border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                      >
                        Exit Playback
                      </button>
                    </div>
                  )}

                  {/* Load Playback Button */}
                  {!playbackMode && !processing && processingStatus === 'completed' && (
                    <button
                      onClick={loadPlaybackData}
                      className="w-full py-3 rounded-lg font-medium transition-colors bg-emerald-600 text-white hover:bg-emerald-700"
                      style={{ borderRadius: 'var(--radius-button)' }}
                    >
                      🎬 Load Playback Mode (Instant Replay)
                    </button>
                  )}
                </div>
              )}
            </section>

            {/* Swimmer List */}
            <SwimmerList swimmers={swimmers} />
          </div>

          {/* Right Column: Priority Dashboard (1/3 width) */}
          <div className="lg:col-span-1 space-y-6">
            {/* Audio Control */}
            <div className="card flex items-center justify-between p-4">
              <span className="card-title">Audio Alerts</span>
              <button
                onClick={toggleAudio}
                className={`btn-toggle px-4 py-2 ${audioEnabled ? 'btn-toggle-active bg-emerald-600 hover:bg-emerald-700' : 'btn-toggle-inactive'}`}
              >
                {audioEnabled ? '🔊 ON' : '🔇 OFF'}
              </button>
            </div>

            {/* Priority Dashboard */}
            <PriorityDashboard
              alerts={alerts}
              onAcknowledge={handleAcknowledgeAlert}
              onFocus={handleFocusSwimmer}
              audioEnabled={audioEnabled}
            />

            {/* System Status */}
            <section className="card p-5" aria-label="System status">
              <h3 className="card-title-lg mb-4 flex items-center gap-2">
                <span aria-hidden>ℹ️</span>
                System Status
              </h3>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-600">Backend API</dt>
                  <dd className="font-medium text-emerald-600">Online</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-600">WebSocket</dt>
                  <dd className={`font-medium ${wsConnected ? 'text-emerald-600' : 'text-red-600'}`}>
                    {wsConnected ? 'Connected' : 'Disconnected'}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-600">AI Pipeline</dt>
                  <dd className={`font-medium ${swimmers.length > 0 ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {swimmers.length > 0 ? 'Active' : 'Waiting'}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-600">Video</dt>
                  <dd className={`font-medium ${
                    processingStatus === 'processing' ? 'text-blue-600' :
                    processingStatus === 'completed' ? 'text-emerald-600' : 'text-slate-600'
                  }`}>
                    {processingStatus === 'idle' ? 'No video' :
                     processingStatus === 'uploading' ? 'Uploading…' :
                     processingStatus === 'processing' ? 'Processing…' :
                     processingStatus === 'completed' ? 'Complete' :
                     processingStatus === 'error' ? 'Error' : 'Ready'}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-600">Data stream</dt>
                  <dd className={`font-medium ${
                    frameResults.length > 0 ? 'text-emerald-600' : wsConnected ? 'text-amber-600' : 'text-slate-500'
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
          </div>
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
