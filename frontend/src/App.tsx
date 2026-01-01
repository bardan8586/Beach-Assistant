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

function App() {
  const [uploadedVideo, setUploadedVideo] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string>('')
  const [processing, setProcessing] = useState(false)
  const [processingStatus, setProcessingStatus] = useState<string>('idle')
  
  // Get data from store
  const { 
    swimmers, 
    showBoundingBoxes, 
    showHeatmap, 
    selectedCamera,
    updateSwimmers,
    setIsConnected,
    toggleBoundingBoxes,
    toggleHeatmap,
    setSelectedCamera
  } = useAppStore()

  // Connect WebSocket for real-time updates
  const { isConnected: wsConnected } = useWebSocket({
    cameraId: selectedCamera,
    onMessage: (message) => {
      console.log('📨 WebSocket message:', message)
      if (message.type === 'swimmers') {
        // Convert backend format to frontend format
        const formattedSwimmers = message.data.map((s: any) => ({
          track_id: s.track_id,
          camera_id: message.camera_id,
          bbox: s.bbox,
          confidence: s.confidence || 0.8,
          first_seen: s.first_seen || new Date().toISOString(),
          last_seen: s.last_seen || new Date().toISOString(),
          status: 'active' as const
        }))
        console.log(`✅ Updated ${formattedSwimmers.length} swimmers`)
        updateSwimmers(formattedSwimmers)
      }
    }
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
    
    // Create object URL for preview
    const url = URL.createObjectURL(file)
    setVideoUrl(url)

    try {
      // Upload video to backend
      setProcessingStatus('uploading')
      const uploadResult = await videoService.uploadVideo(file)
      
      // Generate camera ID from video ID
      const cameraId = `upload_${uploadResult.video_id.substring(0, 8)}`
      setSelectedCamera(cameraId)
      
      // Start AI processing
      setProcessingStatus('processing')
      setProcessing(true)
      const processResult = await videoService.processVideo(uploadResult.video_id, cameraId)
      
      console.log('🚀 AI processing started:', processResult)
      setProcessingStatus('processing')
      
      // Poll for status updates
      const statusInterval = setInterval(async () => {
        if (uploadResult.video_id) {
          const status = await videoService.getStatus(uploadResult.video_id)
          if (status.status === 'completed') {
            clearInterval(statusInterval)
            setProcessingStatus('completed')
            setProcessing(false)
          }
        }
      }, 2000)
      
    } catch (error) {
      console.error('Error processing video:', error)
      setProcessingStatus('error')
      setProcessing(false)
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
                  <div className="flex space-x-2">
                    <button
                      onClick={toggleBoundingBoxes}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                        showBoundingBoxes
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      {showBoundingBoxes ? '✓' : ''} Boxes
                    </button>
                    <button
                      onClick={toggleHeatmap}
                      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                        showHeatmap
                          ? 'bg-primary-600 text-white'
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
                    swimmers={swimmers}
                    showBoundingBoxes={showBoundingBoxes}
                    showHeatmap={showHeatmap}
                    cameraId={selectedCamera}
                    videoUrl={videoUrl}
                  />
                  
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
                </div>
              )}
            </div>

            {/* Swimmer List */}
            <SwimmerList swimmers={swimmers} />
          </div>

          {/* Right Column: Alerts & Info (1/3 width) */}
          <div className="lg:col-span-1 space-y-6">
            <AlertPanel alerts={[]} />
            
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
      <DataDebugPanel swimmers={swimmers} isConnected={wsConnected} />
    </div>
  )
}

export default App
