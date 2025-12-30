/**
 * Main App Component
 * ===================
 * Root component for Beach Safety Monitor dashboard
 */

import { useEffect } from 'react'
import './index.css'

// Components
import Header from './components/Layout/Header'
import StatsCard from './components/Stats/StatsCard'
import VideoPlayer from './components/VideoFeed/VideoPlayer'
import AlertPanel from './components/Alerts/AlertPanel'

// Hooks & Services
import { useAppStore } from './store/useAppStore'
import { useWebSocket } from './hooks/useWebSocket'
import { apiService } from './services/api'

function App() {
  const {
    selectedCamera,
    swimmers,
    alerts,
    isConnected,
    showBoundingBoxes,
    showHeatmap,
    setSwimmers,
    setAlerts,
    setIsConnected,
    updateSwimmers,
    addAlert,
    acknowledgeAlert: acknowledgeAlertInStore,
  } = useAppStore()

  // WebSocket connection for real-time updates
  const { isConnected: wsConnected } = useWebSocket({
    cameraId: selectedCamera,
    onMessage: (message) => {
      switch (message.type) {
        case 'swimmers':
          updateSwimmers(message.data)
          break
        case 'alert':
          addAlert(message.data)
          break
        default:
          break
      }
    },
  })

  // Update connection status
  useEffect(() => {
    setIsConnected(wsConnected)
  }, [wsConnected, setIsConnected])

  // Fetch initial data on mount
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [swimmersData, alertsData] = await Promise.all([
          apiService.getSwimmers(selectedCamera),
          apiService.getAlerts({ camera_id: selectedCamera, status: 'active' }),
        ])
        setSwimmers(swimmersData)
        setAlerts(alertsData)
      } catch (error) {
        console.error('Failed to fetch initial data:', error)
      }
    }

    fetchInitialData()
  }, [selectedCamera, setSwimmers, setAlerts])

  // Handle alert acknowledgment
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await apiService.acknowledgeAlert(alertId)
      acknowledgeAlertInStore(alertId)
    } catch (error) {
      console.error('Failed to acknowledge alert:', error)
    }
  }

  // Calculate statistics
  const activeSwimmers = swimmers.filter((s) => s.status === 'active').length
  const activeAlerts = alerts.filter((a) => a.status === 'active').length
  const avgTimeInWater = swimmers.length > 0
    ? Math.round(
        swimmers.reduce((sum, s) => {
          const timeInWater =
            (new Date(s.last_seen).getTime() - new Date(s.first_seen).getTime()) / 1000
          return sum + timeInWater
        }, 0) / swimmers.length
      )
    : 0

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <Header selectedCamera={selectedCamera} isConnected={isConnected} />

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Stats Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            title="Active Swimmers"
            value={activeSwimmers}
            icon="🏊"
            color="blue"
            subtitle="Currently in water"
          />
          <StatsCard
            title="Avg Time in Water"
            value={avgTimeInWater > 0 ? formatTime(avgTimeInWater) : '--:--'}
            icon="⏱️"
            color="gray"
            subtitle="Per swimmer"
          />
          <StatsCard
            title={activeAlerts > 0 ? 'Active Alerts' : 'All Clear'}
            value={activeAlerts}
            icon={activeAlerts > 0 ? '🚨' : '✅'}
            color={activeAlerts > 0 ? 'red' : 'green'}
            subtitle={activeAlerts > 0 ? 'Requires attention' : 'No alerts'}
          />
        </div>

        {/* Main Grid: Video + Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Feed - Takes 2 columns */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <span className="mr-2">📹</span>
                Live Feed - {selectedCamera}
              </h2>
              <VideoPlayer
                swimmers={swimmers}
                showBoundingBoxes={showBoundingBoxes}
                showHeatmap={showHeatmap}
                cameraId={selectedCamera}
              />
            </div>

            {/* Connection Info */}
            <div className="mt-4">
              {isConnected ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-green-600">✅</span>
                    <div>
                      <p className="text-sm text-green-900 font-medium">
                        Connected to Backend
                      </p>
                      <p className="text-xs text-green-700 mt-1">
                        Receiving real-time updates via WebSocket
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-yellow-600">⚠️</span>
                    <div>
                      <p className="text-sm text-yellow-900 font-medium">
                        Connecting to Backend...
                      </p>
                      <p className="text-xs text-yellow-700 mt-1">
                        Make sure backend is running at http://localhost:8000
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Alerts Panel - Takes 1 column */}
          <div className="lg:col-span-1">
            <AlertPanel alerts={alerts} onAcknowledge={handleAcknowledgeAlert} />
          </div>
        </div>

        {/* Swimmer List (optional, for debugging) */}
        {swimmers.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Tracked Swimmers</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">Track ID</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Confidence</th>
                    <th className="px-4 py-2 text-left">First Seen</th>
                    <th className="px-4 py-2 text-left">Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {swimmers.map((swimmer) => (
                    <tr key={swimmer.track_id} className="border-t">
                      <td className="px-4 py-2 font-mono">#{swimmer.track_id}</td>
                      <td className="px-4 py-2">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            swimmer.status === 'active'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {swimmer.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">{swimmer.confidence.toFixed(2)}</td>
                      <td className="px-4 py-2 text-xs text-gray-600">
                        {new Date(swimmer.first_seen).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-2 text-xs text-gray-600">
                        {new Date(swimmer.last_seen).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
