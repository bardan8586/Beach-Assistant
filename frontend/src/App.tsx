/**
 * Main App Component - Complete Video Processing Dashboard
 * ========================================================
 * Full workflow: Upload video -> Process with AI -> Real-time tracking display
 */

import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import './index.css'

// Components
import Console from './components/Dashboard/Console'
import type { ApiPhase } from './components/Dashboard/Console'
import { derivePatrolState } from './utils/patrolRisk'
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
  const [apiPhase, setApiPhase] = useState<ApiPhase>('checking')
  const [timeline, setTimeline] = useState<AlertData[]>([])

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
  const { isConnected: wsConnected, connectionState } = useWebSocket({
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
            detection_class: (s as { detection_class?: string }).detection_class,
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
    let cancelled = false
    let misses = 0
    const probe = () => {
      void apiService.probeApi().then((phase) => {
        if (cancelled) return
        if (phase === 'online') {
          misses = 0
          setApiPhase('online')
          return
        }
        misses += 1
        setApiPhase(misses >= 12 ? 'offline' : 'waking')
      })
    }
    probe()
    const timer = window.setInterval(probe, 5000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    setTimeline((previous) => {
      const next = new Map(previous.map((item) => [item.alert_id, item]))
      let changed = false
      for (const alert of alerts) {
        const existing = next.get(alert.alert_id)
        if (!existing) {
          next.set(alert.alert_id, alert)
          changed = true
        } else if (existing.acknowledged !== alert.acknowledged) {
          next.set(alert.alert_id, { ...existing, acknowledged: alert.acknowledged })
          changed = true
        }
      }
      if (!changed) return previous
      return Array.from(next.values()).sort((a, b) => b.timestamp - a.timestamp).slice(0, 40)
    })
  }, [alerts])

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

  const apiOnline = apiPhase === 'online' ? true : apiPhase === 'checking' ? null : false
  const patrol = derivePatrolState({
    apiOnline,
    apiPhase,
    wsConnected,
    analyzing: processing || processingStatus === 'uploading',
    hasClip: Boolean(uploadedVideo),
    alerts,
    swimmers,
  })

  return (
    <Console
      apiPhase={apiPhase}
      connectionState={connectionState}
      patrol={patrol}
      swimmers={swimmers}
      alerts={alerts}
      timeline={timeline}
      frameCount={frameResults.length}
      selectedCamera={selectedCamera}
      uploadedVideo={uploadedVideo}
      videoUrl={videoUrl}
      frameResults={frameResults}
      processing={processing}
      processingStatus={processingStatus}
      uploadProgress={uploadProgress}
      playbackMode={playbackMode}
      playbackError={playbackError}
      audioEnabled={audioEnabled}
      autoAnalyze={autoAnalyze}
      openCvWindow={openCvWindow}
      maxUploadBytes={maxUploadBytes}
      showBoundingBoxes={showBoundingBoxes}
      showHeatmap={showHeatmap}
      showZones={showZones}
      focusedSwimmer={focusedSwimmer ?? null}
      onVideoFile={(file) => { void handleVideoSelected(file) }}
      onReject={setPlaybackError}
      onReset={handleResetUpload}
      onStart={() => { void handleStartProcessing() }}
      onLoadPlayback={() => { void loadPlaybackData() }}
      onExitPlayback={() => setPlaybackMode(false)}
      onDismissError={() => setPlaybackError(null)}
      onAcknowledge={(id) => { void handleAcknowledgeAlert(id) }}
      onFocus={handleFocusSwimmer}
      onExitFocus={handleExitFocus}
      onToggleAudio={toggleAudio}
      onToggleBoxes={toggleBoundingBoxes}
      onToggleHeatmap={toggleHeatmap}
      onToggleZones={toggleZones}
      onAutoAnalyze={setAutoAnalyze}
      onOpenCv={setOpenCvWindow}
    />
  )

}

export default App
