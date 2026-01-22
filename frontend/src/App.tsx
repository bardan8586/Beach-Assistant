/**
 * Main App Component - Complete Video Processing Dashboard
 * ========================================================
 * Full workflow: Upload video -> Process with AI -> Real-time tracking display
 */

import { useEffect, useState } from 'react'
import './index.css'

// Components
import DetailedStats from './components/Stats/DetailedStats'
import VideoPlayer from './components/VideoFeed/VideoPlayer'
import SwimmerList from './components/Swimmers/SwimmerList'
import AlertPanel from './components/Alerts/AlertPanel'
import VideoUploader from './components/VideoUpload/VideoUploader'
import DataDebugPanel from './components/Debug/DataDebugPanel'
import { useAppStore } from './store/useAppStore'
import { useWebSocket } from './hooks/useWebSocket'
import { apiService } from './services/api'
import { videoService } from './services/videoService'
import { playbackService } from './services/playbackService'
import type { FrameResult } from './types/frameResult'

function App() {
  const [uploadedVideo, setUploadedVideo] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string>('')
  const [videoId, setVideoId] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [processingStatus, setProcessingStatus] = useState<string>('idle')
  
  // FrameResult data for playback mode
  const [frameResults, setFrameResults] = useState<FrameResult[]>([])
  const [playbackMode, setPlaybackMode] = useState(false)  // true = playback, false = live
  
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
      
      if (message.type === 'swimmers') {
        console.log('   Swimmers data:', message.data)
        
        // Only process if it's for the current camera or 'all'
        if (message.camera_id === selectedCamera || message.camera_id === 'all') {
          // Convert backend format to frontend format
          const formattedSwimmers = message.data.map((s: any) => {
            console.log('   Processing swimmer:', s)
            return {
              track_id: s.track_id,
              camera_id: message.camera_id,
              bbox: s.bbox || { x1: 0, y1: 0, x2: 0, y2: 0 },
              confidence: s.confidence || 0.8,
              first_seen: s.first_seen || new Date().toISOString(),
              last_seen: s.last_seen || new Date().toISOString(),
              status: 'active' as const
            }
          })
          console.log(`✅ Updated ${formattedSwimmers.length} swimmers for camera ${message.camera_id}`)
          console.log('   Formatted swimmers:', formattedSwimmers)
          updateSwimmers(formattedSwimmers)
        } else {
          console.log(`⚠️ Ignoring message for different camera: ${message.camera_id} (current: ${selectedCamera})`)
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
              
              // Auto-load playback data when processing completes
              console.log('🎬 Loading playback data...')
              const results = await playbackService.loadFrameResults(uploadResult.video_id)
              setFrameResults(results)
              setPlaybackMode(true)
              console.log(`✅ Playback mode activated with ${results.length} frames`)
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
    try {
      console.log('🎬 Manually loading playback data...')
      const results = await playbackService.loadFrameResults(videoId)
      setFrameResults(results)
      setPlaybackMode(true)
      console.log(`✅ Loaded ${results.length} frames for playback`)
    } catch (error) {
      console.error('Failed to load playback data:', error)
      alert('No playback data available yet. Wait for processing to complete.')
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Professional Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-4xl">🏖️</div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Beach Safety Monitor
                </h1>
                <p className="text-sm text-gray-600">
                  Upload video → AI Processing → Real-time Tracking
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-6">
              <div className="text-right">
                <div className="text-xs text-gray-500 uppercase tracking-wide">Connection</div>
                <div className="flex items-center space-x-2 mt-1">
                  <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                  <span className={`text-sm font-medium ${wsConnected ? 'text-green-600' : 'text-red-600'}`}>
                    {wsConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                {!wsConnected && (
                  <div className="text-xs text-red-500 mt-1">
                    Check console for errors
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500 uppercase tracking-wide">Camera</div>
                <div className="text-sm font-semibold text-gray-900 mt-1">{selectedCamera}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500 uppercase tracking-wide">Status</div>
                <div className={`text-sm font-semibold mt-1 ${
                  processingStatus === 'processing' ? 'text-blue-600' :
                  processingStatus === 'completed' ? 'text-green-600' :
                  processingStatus === 'error' ? 'text-red-600' :
                  'text-gray-600'
                }`}>
                  {processingStatus === 'uploading' ? '📤 Uploading...' :
                   processingStatus === 'processing' ? '🤖 Processing...' :
                   processingStatus === 'completed' ? '✅ Complete' :
                   processingStatus === 'error' ? '❌ Error' :
                   'Ready'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

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

          {/* Right Column: Alerts & Info (1/3 width) */}
          <div className="lg:col-span-1 space-y-6">
            <AlertPanel 
              alerts={[]} 
              onAcknowledge={async (alertId) => {
                try {
                  await apiService.acknowledgeAlert(alertId)
                  // Refresh alerts or update state
                } catch (error) {
                  console.error('Failed to acknowledge alert:', error)
                }
              }}
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
    </div>
  )
}

export default App
