/**
 * Main App Component - Professional Dashboard
 * ===========================================
 * Complete beach safety monitoring dashboard with all tracking data
 */

import { useEffect } from 'react'
import './index.css'

// Components
import DetailedStats from './components/Stats/DetailedStats'
import VideoPlayer from './components/VideoFeed/VideoPlayer'
import SwimmerList from './components/Swimmers/SwimmerList'
import AlertPanel from './components/Alerts/AlertPanel'
import DataDebugPanel from './components/Debug/DataDebugPanel'
import { useAppStore } from './store/useAppStore'
import { useWebSocket } from './hooks/useWebSocket'
import { apiService } from './services/api'

function App() {
  
  // Get data from store
  const { 
    swimmers, 
    showBoundingBoxes, 
    showHeatmap, 
    selectedCamera,
    updateSwimmers,
    setIsConnected,
    toggleBoundingBoxes,
    toggleHeatmap
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
                  Real-time AI Swimmer Detection & Tracking System
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
                <div className="text-xs text-gray-500 uppercase tracking-wide">Time</div>
                <div className="text-sm font-mono text-gray-900 mt-1">
                  {new Date().toLocaleTimeString()}
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
          {/* Left Column: Video Feed (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Video Player */}
            <div className="bg-white rounded-lg shadow-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900 flex items-center">
                  <span className="mr-2">📹</span>
                  Live Video Feed
                </h2>
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
              </div>
              <VideoPlayer
                swimmers={swimmers}
                showBoundingBoxes={showBoundingBoxes}
                showHeatmap={showHeatmap}
                cameraId={selectedCamera}
              />
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
                  <span className="text-gray-600">Data Updates:</span>
                  <span className="font-medium text-gray-900">Real-time</span>
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
