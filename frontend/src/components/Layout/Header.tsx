/**
 * Header Component
 * ================
 * Top navigation bar with status indicators
 */

import { useState, useEffect } from 'react'

interface HeaderProps {
  selectedCamera: string
  isConnected: boolean
}

export default function Header({ selectedCamera, isConnected }: HeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <span className="text-3xl">🏖️</span>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Beach Safety Monitor
              </h1>
              <p className="text-xs text-gray-500">
                Real-time AI Surveillance System
              </p>
            </div>
          </div>

          {/* Status Indicators */}
          <div className="flex items-center space-x-6">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div 
                className={`w-2 h-2 rounded-full ${
                  isConnected 
                    ? 'bg-green-500 animate-pulse' 
                    : 'bg-red-500'
                }`}
              />
              <span className="text-sm text-gray-600">
                {isConnected ? 'Live' : 'Disconnected'}
              </span>
            </div>

            {/* Camera ID */}
            <div className="text-sm text-gray-600">
              <span className="font-medium">Camera:</span> {selectedCamera}
            </div>

            {/* Current Time */}
            <div className="text-sm text-gray-600 font-mono">
              {currentTime.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}


