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
      console.log('📨 WebSocket message received:', message)
      console.log('   Current camera:', selectedCamera)
      console.log('   Message camera:', message.camera_id)
      
      // Handle FrameResult messages (new format with alerts)
      if (message.swimmers || message.alerts) {
        console.log('   FrameResult received:', message)
        
        // Update alerts if present
        if (message.alerts && Array.isArray(message.alerts)) {
          setAlerts(message.alerts)
          
          // Trigger audio alerts for new urgent alerts
          message.alerts.forEach((alert: { alert_id: string; level: string; swimmer_id: number; zone: string; action_recommended: string; acknowledged?: boolean }) => {
            if (!alert.acknowledged && (alert.level === 'emergency' || alert.level === 'alert')) {
              audioAlertService.speakAlert(
                alert.swimmer_id,
                alert.level,
                alert.zone,
                alert.action_recommended,
                alert.alert_id
              )
            }
          })
        }
        
        // Update swimmers if present
        if (message.swimmers && Array.isArray(message.swimmers)) {
          const formattedSwimmers = message.swimmers.map((s: { track_id: number; bbox?: { x: number; y: number; w: number; h: number }; confidence?: number; risk_score?: number; risk_level?: string; behavior?: string; zone?: string; time_in_water?: number; velocity?: number }) => ({
            track_id: s.track_id,
            camera_id: message.camera_id || selectedCamera,
            bbox: s.bbox || { x: 0, y: 0, w: 0, h: 0 },
            confidence: s.confidence || 0.8,
            risk_score: s.risk_score || 0,
            risk_level: s.risk_level || 'LOW',
            behavior: s.behavior || 'NORMAL',
            zone: s.zone || 'SAFE',
            time_in_water: s.time_in_water || 0,
            velocity: s.velocity || 0,
            first_seen: new Date().toISOString(),
            last_seen: new Date().toISOString(),
            status: 'active' as const
          }))
          updateSwimmers(formattedSwimmers)
        }
      }
      // Legacy format support
      else if (message.type === 'swimmers' && message.data && Array.isArray(message.data)) {
        const data = message.data as Array<{ track_id: number; bbox?: unknown; first_seen?: string; last_seen?: string; confidence?: number }>
        if (message.camera_id === selectedCamera || message.camera_id === 'all') {
          const formattedSwimmers = data.map((s) => ({
            track_id: s.track_id,
            camera_id: message.camera_id ?? selectedCamera,
            bbox: s.bbox || { x1: 0, y1: 0, x2: 0, y2: 0 },
            confidence: s.confidence || 0.8,
            first_seen: s.first_seen || new Date().toISOString(),
            last_seen: s.last_seen || new Date().toISOString(),
            status: 'active' as const
          }))
          updateSwimmers(formattedSwimmers)
        }
      } else {
        console.log('   Unknown message type:', message.type)
      }
    },
    autoConnect: true  // Always auto-connect
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

  // Handle video file selection
  const handleVideoSelected = async (file: File) => {
    setUploadedVideo(file)
    setFrameResults([])  // Clear previous results
    setPlaybackMode(false)  // Start in live mode
    
    // Create object URL for preview
    const url = URL.createObjectURL(file)
    setVideoUrl(url)

    try {
      // Upload video to backend
      setProcessingStatus('uploading')
      const uploadResult = await videoService.uploadVideo(file)
      setVideoId(uploadResult.video_id)
      
      // Generate camera ID from video ID (use first 8 chars)
      const cameraId = `upload_${uploadResult.video_id.substring(0, 8)}`
      console.log(`📹 Setting camera ID: ${cameraId}`)
      setSelectedCamera(cameraId)
      
      // Wait a moment for WebSocket to reconnect with new camera_id
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Start AI processing
      setProcessingStatus('processing')
      setProcessing(true)
      const processResult = await videoService.processVideo(uploadResult.video_id, cameraId)
      
      console.log('🚀 AI processing started:', processResult)
      console.log(`   Camera ID: ${cameraId}`)
      console.log(`   Video ID: ${uploadResult.video_id}`)
      setProcessingStatus('processing')
      
      // Poll for status updates
      const statusInterval = setInterval(async () => {
        if (uploadResult.video_id) {
          try {
            const status = await videoService.getStatus(uploadResult.video_id)
            if (status.status === 'completed') {
              clearInterval(statusInterval)
              setProcessingStatus('completed')
              setProcessing(false)
              setPlaybackError(null)
              try {
                const results = await playbackService.loadFrameResults(uploadResult.video_id)
                setFrameResults(results)
                setPlaybackMode(true)
              } catch {
                setPlaybackError('Processing finished but results could not be loaded. Use "Load results" to retry.')
              }
            }
          } catch (error) {
            console.error('Status check error:', error)
          }
        }
      }, 2000)
      
      // Store interval to cleanup if component unmounts
      return () => clearInterval(statusInterval)
      
    } catch (error) {
      console.error('Error processing video:', error)
      setProcessingStatus('error')
      setProcessing(false)
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
    <div className="min-h-screen bg-slate-100">
      <Header
        selectedCamera={selectedCamera}
        isConnected={wsConnected}
        processingStatus={processingStatus}
      />

      {/* Main Dashboard */}
      <main className="container mx-auto px-6 py-6">
        {/* Top Stats Row */}
        <div className="mb-6">
          <DetailedStats swimmers={swimmers} />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column: Video Section (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Video Upload or Player */}
            <div className="bg-white rounded-lg shadow-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900 flex items-center">
                  <span className="mr-2">📹</span>
                  {uploadedVideo ? 'Video Analysis' : 'Upload Video'}
                </h2>
                {uploadedVideo && (
                  <div className="flex items-center space-x-3">
                    {playbackMode && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded font-medium">
                        🎬 PLAYBACK
                      </span>
                    )}
                    <button
                      onClick={toggleBoundingBoxes}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                        showBoundingBoxes
                          ? 'bg-green-600 text-white shadow-lg'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      {showBoundingBoxes ? '✓' : ''} Boxes
                    </button>
                    <button
                      onClick={toggleZones}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                        showZones
                          ? 'bg-blue-600 text-white shadow-lg'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      {showZones ? '✓' : ''} Zones
                    </button>
                    <button
                      onClick={toggleHeatmap}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                        showHeatmap
                          ? 'bg-purple-600 text-white shadow-lg'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      {showHeatmap ? '✓' : ''} Heatmap
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
                  
                  {/* Processing Status */}
                  {processing && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-center space-x-3">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                        <div>
                          <div className="font-medium text-blue-900">AI Processing Active</div>
                          <div className="text-sm text-blue-700">
                            Detecting swimmers and tracking in real-time...
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Playback Mode Indicator */}
                  {playbackMode && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="text-2xl">🎬</div>
                          <div>
                            <div className="font-medium text-green-900">Playback Mode</div>
                            <div className="text-sm text-green-700">
                              {frameResults.length} frames loaded | Pixel-perfect overlays active
                            </div>
                          </div>
                        </div>
                        <button 
                          onClick={() => setPlaybackMode(false)}
                          className="px-3 py-1.5 bg-white border border-green-300 text-green-700 rounded text-sm hover:bg-green-50"
                        >
                          Exit Playback
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {/* Load Playback Button */}
                  {!playbackMode && !processing && processingStatus === 'completed' && (
                    <button
                      onClick={loadPlaybackData}
                      className="w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
                    >
                      🎬 Load Playback Mode (Instant Replay)
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Swimmer List */}
            <SwimmerList swimmers={swimmers} />
          </div>

          {/* Right Column: Priority Dashboard (1/3 width) */}
          <div className="lg:col-span-1 space-y-6">
            {/* Audio Control */}
            <div className="flex items-center justify-between bg-white rounded-lg shadow p-3">
              <span className="text-sm font-medium text-gray-700">Audio Alerts</span>
              <button
                onClick={toggleAudio}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  audioEnabled 
                    ? 'bg-green-600 text-white hover:bg-green-700' 
                    : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                }`}
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
            
            {/* System Info */}
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">ℹ️</span>
                System Status
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Backend API:</span>
                  <span className="font-medium text-green-600">Online</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">WebSocket:</span>
                  <span className={`font-medium ${wsConnected ? 'text-green-600' : 'text-red-600'}`}>
                    {wsConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">AI Pipeline:</span>
                  <span className={`font-medium ${swimmers.length > 0 ? 'text-green-600' : 'text-yellow-600'}`}>
                    {swimmers.length > 0 ? 'Active' : 'Waiting'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Video Status:</span>
                  <span className={`font-medium ${
                    processingStatus === 'processing' ? 'text-blue-600' :
                    processingStatus === 'completed' ? 'text-green-600' :
                    'text-gray-600'
                  }`}>
                    {processingStatus === 'idle' ? 'No video' :
                     processingStatus === 'uploading' ? 'Uploading...' :
                     processingStatus === 'processing' ? 'Processing...' :
                     processingStatus === 'completed' ? 'Complete' :
                     processingStatus === 'error' ? 'Error' : 'Ready'}
                  </span>
                </div>
              </div>
            </div>
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
