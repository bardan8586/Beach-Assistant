/**
 * Main App Component
 * ===================
 * Beach Safety Monitor Dashboard with Video Processing
 */

import { useState, useEffect } from 'react'
import './index.css'

// Components
import StatsCard from './components/Stats/StatsCard'
import VideoUploader from './components/VideoUpload/VideoUploader'
import VideoProcessor from './components/VideoFeed/VideoProcessor'
import AlertPanel from './components/Alerts/AlertPanel'
import VideoPlayer from './components/VideoFeed/VideoPlayer'
import { useAppStore } from './store/useAppStore'
import { useWebSocket } from './hooks/useWebSocket'
import { apiService } from './services/api'

function App() {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [activeTab, setActiveTab] = useState<'upload' | 'live'>('live')  // Start on live tab
  
  // Get data from store
  const { 
    swimmers, 
    showBoundingBoxes, 
    showHeatmap, 
    selectedCamera,
    updateSwimmers,
    setIsConnected
  } = useAppStore()

  // Connect WebSocket for real-time updates
  const { isConnected: wsConnected } = useWebSocket({
    cameraId: selectedCamera,
    onMessage: (message) => {
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
        updateSwimmers(formattedSwimmers)
      }
    }
  })

  // Update connection status
  useEffect(() => {
    setIsConnected(wsConnected)
  }, [wsConnected, setIsConnected])

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const swimmersData = await apiService.getSwimmers(selectedCamera)
        updateSwimmers(swimmersData)
      } catch (error) {
        console.error('Failed to fetch initial swimmers:', error)
      }
    }
    fetchData()
    // Refresh every 5 seconds as fallback
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [selectedCamera, updateSwimmers])

  // Calculate stats from actual data
  const stats = {
    activeSwimmers: swimmers.length,
    avgTime: swimmers.length > 0 ? '2:30' : '--:--', // TODO: Calculate from swimmer timestamps
    totalAlerts: 0,
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-md border-b-2 border-primary-100">
        <div className="px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-5xl">🏖️</div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-600 to-blue-500 bg-clip-text text-transparent">
                  Beach Safety Monitor
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  AI-Powered Swimmer Detection & Tracking
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <div className="text-sm text-gray-500">Status</div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm font-medium text-green-600">Online</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Stats Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            title="Active Swimmers"
            value={stats.activeSwimmers}
            icon="🏊"
            color="blue"
            subtitle="Currently detected"
          />
          <StatsCard
            title="Avg Time in Water"
            value={stats.avgTime}
            icon="⏱️"
            color="gray"
            subtitle="Per swimmer"
          />
          <StatsCard
            title="Safety Status"
            value={stats.totalAlerts === 0 ? '✅' : `${stats.totalAlerts}`}
            icon={stats.totalAlerts > 0 ? '🚨' : '✅'}
            color={stats.totalAlerts > 0 ? 'red' : 'green'}
            subtitle={stats.totalAlerts > 0 ? 'Active alerts' : 'All clear'}
          />
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-t-lg shadow-sm border-b">
          <div className="flex space-x-1 p-1">
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                activeTab === 'upload'
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              📁 Upload & Process Video
            </button>
            <button
              onClick={() => setActiveTab('live')}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                activeTab === 'live'
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              📹 Live Camera Feed
            </button>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Section - Takes 2 columns */}
          <div className="lg:col-span-2 bg-white rounded-b-lg shadow-lg p-6">
            {activeTab === 'upload' ? (
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-2 flex items-center">
                    <span className="mr-2">🎥</span>
                    Upload Video for AI Analysis
                  </h2>
                  <p className="text-sm text-gray-600 mb-4">
                    Upload a beach video to detect and track swimmers automatically
                  </p>
                </div>
                
                {!videoFile ? (
                  <VideoUploader onVideoSelected={setVideoFile} />
                ) : (
                  <VideoProcessor videoFile={videoFile} />
                )}
              </div>
            ) : (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold flex items-center">
                  <span className="mr-2">📹</span>
                  Live Camera Feed
                </h2>
                <VideoPlayer
                  swimmers={swimmers}
                  showBoundingBoxes={showBoundingBoxes}
                  showHeatmap={showHeatmap}
                  cameraId={selectedCamera}
                />
              </div>
            )}
          </div>

          {/* Alerts Panel - Takes 1 column */}
          <div className="lg:col-span-1">
            <AlertPanel alerts={[]} />
          </div>
        </div>

        {/* Info Banner */}
        <div className="mt-8 bg-gradient-to-r from-blue-50 to-primary-50 border-2 border-primary-200 rounded-lg p-6">
          <div className="flex items-start space-x-4">
            <div className="text-4xl">💡</div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                How It Works
              </h3>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-center">
                  <span className="text-green-500 mr-2">✓</span>
                  Upload beach video or connect live camera
                </li>
                <li className="flex items-center">
                  <span className="text-green-500 mr-2">✓</span>
                  YOLOv8 AI detects people in water
                </li>
                <li className="flex items-center">
                  <span className="text-green-500 mr-2">✓</span>
                  ByteTrack assigns unique IDs to each swimmer
                </li>
                <li className="flex items-center">
                  <span className="text-green-500 mr-2">✓</span>
                  Real-time alerts for potential safety issues
                </li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
