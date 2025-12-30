/**
 * Main App Component
 * ===================
 * Beach Safety Monitor Dashboard with Video Processing
 */

import { useState } from 'react'
import './index.css'

// Components
import StatsCard from './components/Stats/StatsCard'
import VideoUploader from './components/VideoUpload/VideoUploader'
import VideoProcessor from './components/VideoFeed/VideoProcessor'
import AlertPanel from './components/Alerts/AlertPanel'

function App() {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [activeTab, setActiveTab] = useState<'upload' | 'live'>('upload')

  // Mock stats (in real app, would come from API)
  const stats = {
    activeSwimmers: 0,
    avgTime: '--:--',
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
                <div className="bg-gray-900 rounded-lg h-96 flex items-center justify-center">
                  <div className="text-center text-white">
                    <div className="text-6xl mb-4">📹</div>
                    <p className="text-xl font-medium">Live Feed Mode</p>
                    <p className="text-sm text-gray-400 mt-2">
                      Connect RTSP camera or run AI pipeline
                    </p>
                    <p className="text-xs text-gray-500 mt-4">
                      Backend: http://localhost:8000
                    </p>
                  </div>
                </div>
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
