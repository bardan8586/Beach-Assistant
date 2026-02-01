/**
 * Focus Mode Component
 * ====================
 * Dedicated view for tracking one high-risk swimmer
 * 
 * Features:
 * - Full-screen swimmer focus
 * - Real-time risk graph
 * - Timeline of behavior changes
 * - Zoomed video feed on swimmer
 * - Quick exit to dashboard
 */

import { useEffect, useState } from 'react'
import type { Swimmer } from '../../types/swimmer'

interface FocusModeProps {
  swimmer: Swimmer | null
  onExit: () => void
  videoRef?: HTMLVideoElement | null
}

export default function FocusMode({ swimmer, onExit, videoRef }: FocusModeProps) {
  const [riskHistory, setRiskHistory] = useState<number[]>([])
  
  const riskScore = swimmer?.risk_score ?? 0

  // Track risk score over time
  useEffect(() => {
    if (swimmer) {
      setRiskHistory(prev => [...prev.slice(-60), riskScore])
    }
  }, [swimmer, riskScore])

  if (!swimmer) {
    return null
  }

  const riskColor =
    riskScore >= 90 ? 'text-red-600' :
    riskScore >= 70 ? 'text-orange-600' :
    riskScore >= 50 ? 'text-yellow-600' :
    'text-green-600'
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-95 z-50 flex flex-col">
      {/* Header */}
      <div className="bg-gray-900 p-6 flex items-center justify-between border-b-4 border-red-500">
        <div className="flex items-center space-x-4">
          <div className="text-5xl">🎯</div>
          <div>
            <h1 className="text-4xl font-black text-white">
              SWIMMER #{swimmer.track_id}
            </h1>
            <p className="text-lg text-gray-400">Focus Mode Active</p>
          </div>
        </div>
        
        <button
          onClick={onExit}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-xl text-xl transition-colors"
        >
          ✕ Exit Focus
        </button>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 grid grid-cols-2 gap-6 p-6">
        {/* Left: Swimmer Stats */}
        <div className="space-y-6">
          {/* Risk Score - HUGE */}
          <div className="bg-gray-800 rounded-2xl p-8 text-center">
            <p className="text-gray-400 text-lg mb-2">CURRENT RISK</p>
            <div className={`text-9xl font-black ${riskColor}`}>
              {riskScore.toFixed(0)}
            </div>
            <p className={`text-3xl font-bold mt-4 uppercase ${riskColor}`}>
              {swimmer.risk_level}
            </p>
          </div>
          
          {/* State & Behavior */}
          <div className="bg-gray-800 rounded-2xl p-6">
            <h3 className="text-white text-xl font-bold mb-4">Current State</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">State:</span>
                <span className="text-white font-bold text-lg">{(swimmer as { state?: string }).state ?? 'NORMAL'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Behavior:</span>
                <span className="text-white font-bold">{swimmer.behavior ?? '—'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Zone:</span>
                <span className={`font-bold ${
                  (swimmer.zone === 'DANGER') ? 'text-red-400' :
                  (swimmer.zone === 'CAUTION') ? 'text-yellow-400' :
                  'text-green-400'
                }`}>
                  {swimmer.zone ?? '—'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Time in Water:</span>
                <span className="text-white font-bold">{(swimmer.time_in_water ?? 0).toFixed(0)}s</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Velocity:</span>
                <span className="text-white font-bold">{(swimmer.velocity ?? 0).toFixed(1)} px/s</span>
              </div>
              {(swimmer as { fatigue?: number }).fatigue != null && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Fatigue:</span>
                  <span className="text-orange-400 font-bold">{(swimmer as unknown as { fatigue: number }).fatigue.toFixed(0)}%</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Risk History Graph */}
          <div className="bg-gray-800 rounded-2xl p-6">
            <h3 className="text-white text-xl font-bold mb-4">Risk Trend</h3>
            <div className="h-40 flex items-end space-x-1">
              {riskHistory.map((risk, i) => {
                const height = (risk / 100) * 100
                const barColor = 
                  risk >= 90 ? 'bg-red-500' :
                  risk >= 70 ? 'bg-orange-500' :
                  risk >= 50 ? 'bg-yellow-500' :
                  'bg-green-500'
                
                return (
                  <div
                    key={i}
                    className={`flex-1 ${barColor} rounded-t`}
                    style={{ height: `${height}%` }}
                  />
                )
              })}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>-60s</span>
              <span>Now</span>
            </div>
          </div>
        </div>
        
        {/* Right: Video Feed (zoomed on swimmer) */}
        <div className="bg-gray-800 rounded-2xl p-6">
          <h3 className="text-white text-xl font-bold mb-4">Live Feed</h3>
          <div className="bg-black rounded-xl overflow-hidden aspect-video flex items-center justify-center">
            {videoRef ? (
              <div className="relative w-full h-full">
                {/* Would show zoomed crop of video feed here */}
                <div className="absolute inset-0 flex items-center justify-center text-gray-600">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📹</div>
                    <p>Swimmer #{swimmer.track_id}</p>
                    <p className="text-sm mt-2">Position: ({swimmer.bbox?.x ?? 0}, {swimmer.bbox?.y ?? 0})</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-600 text-center">
                <div className="text-6xl mb-4">📹</div>
                <p>Video feed unavailable</p>
              </div>
            )}
          </div>
          
          {/* Quick Actions */}
          <div className="mt-6 space-y-3">
            <button className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl transition-colors">
              ✓ Mark as Safe
            </button>
            <button className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded-xl transition-colors">
              🚨 Dispatch Rescue
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
