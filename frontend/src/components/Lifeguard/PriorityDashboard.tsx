/**
 * Priority Lifeguard Dashboard
 * ============================
 * Shows TOP 3 HIGHEST-RISK swimmers in large, clear format
 * Designed for split-second decision making in high-stress situations
 * 
 * Features:
 * - TOP 3 view (not overwhelming)
 * - HUGE visual indicators  
 * - Audio alerts with text-to-speech
 * - One-click acknowledge
 * - Action recommendations
 */

import { useEffect, useRef, useState } from 'react'
import type { AlertData } from '../../types/frameResult'

interface PriorityDashboardProps {
  alerts: AlertData[]
  onAcknowledge: (alertId: string) => void
  onFocus: (swimmerId: number) => void
  audioEnabled?: boolean
}

export default function PriorityDashboard({ 
  alerts, 
  onAcknowledge, 
  onFocus,
  audioEnabled = true 
}: PriorityDashboardProps) {
  const [spokenAlerts, setSpokenAlerts] = useState<Set<string>>(new Set())
  const audioContextRef = useRef<AudioContext | null>(null)
  
  // Initialize audio context
  useEffect(() => {
    if (audioEnabled && !audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
    }
  }, [audioEnabled])
  
  // Speak new alerts
  useEffect(() => {
    if (!audioEnabled || !('speechSynthesis' in window)) return
    
    // Find new unacknowledged emergency/alert level alerts
    const urgentAlerts = alerts.filter(
      a => !a.acknowledged && 
           (a.level === 'emergency' || a.level === 'alert') &&
           !spokenAlerts.has(a.alert_id)
    )
    
    urgentAlerts.forEach(alert => {
      speakAlert(alert)
      setSpokenAlerts(prev => new Set([...prev, alert.alert_id]))
    })
  }, [alerts, audioEnabled, spokenAlerts])
  
  const speakAlert = (alert: AlertData) => {
    // Play attention sound first
    playAlertSound(alert.level)
    
    // Then speak the alert
    setTimeout(() => {
      const utterance = new SpeechSynthesisUtterance()
      
      if (alert.level === 'emergency') {
        utterance.text = `Emergency! Swimmer ${alert.swimmer_id}, ${alert.zone} zone. ${alert.action_recommended}`
        utterance.rate = 1.1
        utterance.pitch = 1.2
        utterance.volume = 1.0
      } else {
        utterance.text = `Alert: Swimmer ${alert.swimmer_id}, ${alert.zone} zone. Monitor closely.`
        utterance.rate = 1.0
        utterance.volume = 0.9
      }
      
      window.speechSynthesis.speak(utterance)
    }, 500)
  }
  
  const playAlertSound = (level: string) => {
    if (!audioContextRef.current) return
    
    const ctx = audioContextRef.current
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)
    
    // Different sounds for different levels
    if (level === 'emergency') {
      // Urgent alarm
      oscillator.frequency.value = 880
      gainNode.gain.setValueAtTime(0.3, ctx.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
      oscillator.start(ctx.currentTime)
      oscillator.stop(ctx.currentTime + 0.3)
      
      // Second beep
      setTimeout(() => {
        const osc2 = ctx.createOscillator()
        const gain2 = ctx.createGain()
        osc2.connect(gain2)
        gain2.connect(ctx.destination)
        osc2.frequency.value = 880
        gain2.gain.setValueAtTime(0.3, ctx.currentTime)
        gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
        osc2.start(ctx.currentTime)
        osc2.stop(ctx.currentTime + 0.3)
      }, 400)
    } else if (level === 'alert') {
      // Warning tone
      oscillator.frequency.value = 660
      gainNode.gain.setValueAtTime(0.2, ctx.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4)
      oscillator.start(ctx.currentTime)
      oscillator.stop(ctx.currentTime + 0.4)
    } else {
      // Gentle notification
      oscillator.frequency.value = 440
      gainNode.gain.setValueAtTime(0.1, ctx.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2)
      oscillator.start(ctx.currentTime)
      oscillator.stop(ctx.currentTime + 0.2)
    }
  }
  
  const getLevelColor = (level: string) => {
    switch (level) {
      case 'emergency': return { bg: 'bg-red-600', border: 'border-red-500', text: 'text-red-900', icon: '🔴' }
      case 'alert': return { bg: 'bg-orange-500', border: 'border-orange-400', text: 'text-orange-900', icon: '🟠' }
      case 'watch': return { bg: 'bg-yellow-400', border: 'border-yellow-300', text: 'text-yellow-900', icon: '🟡' }
      default: return { bg: 'bg-gray-400', border: 'border-gray-300', text: 'text-gray-900', icon: '⚪' }
    }
  }
  
  // Get TOP 3 alerts only
  const topAlerts = alerts
    .filter(a => !a.acknowledged)
    .sort((a, b) => {
      // Sort by level (emergency > alert > watch) then risk score
      const levelOrder = { emergency: 0, alert: 1, watch: 2 }
      const levelDiff = levelOrder[a.level] - levelOrder[b.level]
      return levelDiff !== 0 ? levelDiff : b.risk_score - a.risk_score
    })
    .slice(0, 3)
  
  if (topAlerts.length === 0) {
    return (
      <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-2xl shadow-2xl p-12">
        <div className="text-center">
          <div className="text-8xl mb-6">✅</div>
          <h2 className="text-4xl font-bold text-green-800 mb-2">All Clear</h2>
          <p className="text-xl text-green-600">No swimmers at risk</p>
          <p className="text-sm text-green-500 mt-4">
            {alerts.length > 0 ? `${alerts.length} acknowledged alert(s)` : 'System monitoring'}
          </p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-lg p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <h1 className="text-2xl font-bold text-gray-900">Priority Alerts</h1>
          <span className="text-sm text-gray-500">Showing top {topAlerts.length} of {alerts.length}</span>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-sm">
            <span className="font-semibold text-red-600">{alerts.filter(a => a.level === 'emergency' && !a.acknowledged).length}</span>
            <span className="text-gray-500 ml-1">🔴</span>
          </div>
          <div className="text-sm">
            <span className="font-semibold text-orange-600">{alerts.filter(a => a.level === 'alert' && !a.acknowledged).length}</span>
            <span className="text-gray-500 ml-1">🟠</span>
          </div>
          <div className="text-sm">
            <span className="font-semibold text-yellow-600">{alerts.filter(a => a.level === 'watch' && !a.acknowledged).length}</span>
            <span className="text-gray-500 ml-1">🟡</span>
          </div>
        </div>
      </div>
      
      {/* TOP 3 Alerts - BIG CARDS */}
      <div className="grid grid-cols-1 gap-4">
        {topAlerts.map((alert) => {
          const colors = getLevelColor(alert.level)
          const isEmergency = alert.level === 'emergency'
          
          return (
            <div
              key={alert.alert_id}
              className={`
                ${colors.bg} ${isEmergency ? 'animate-pulse-slow' : ''}
                rounded-2xl shadow-2xl overflow-hidden transform transition-all hover:scale-[1.02]
                border-4 ${colors.border}
              `}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-4">
                    <div className="text-6xl">{colors.icon}</div>
                    <div>
                      <div className="flex items-center space-x-3 mb-1">
                        <h3 className="text-4xl font-black text-white">
                          #{alert.swimmer_id}
                        </h3>
                        <span className={`text-xl font-bold uppercase ${colors.text} bg-white px-3 py-1 rounded-full`}>
                          {alert.level}
                        </span>
                      </div>
                      <p className="text-white text-lg font-semibold">
                        {alert.zone.toUpperCase()} ZONE • {alert.duration.toFixed(0)}s
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-5xl font-black text-white mb-1">
                      {alert.risk_score.toFixed(0)}
                    </div>
                    <div className="text-sm text-white opacity-90">
                      Risk Score
                    </div>
                  </div>
                </div>
                
                {/* Context */}
                <div className="bg-white bg-opacity-20 rounded-xl p-4 mb-4">
                  <p className="text-white text-lg font-medium mb-2">
                    {alert.context}
                  </p>
                  <p className="text-white text-sm opacity-90">
                    Confidence: {(alert.confidence * 100).toFixed(0)}%
                  </p>
                </div>
                
                {/* Action Recommendation - BIG */}
                <div className="bg-white rounded-xl p-4 mb-4">
                  <p className={`text-xl font-bold ${colors.text} mb-1`}>
                    {alert.action_recommended}
                  </p>
                  <p className="text-sm text-gray-600">
                    Location: ({alert.location[0]}, {alert.location[1]})
                  </p>
                </div>
                
                {/* Action Buttons */}
                <div className="flex space-x-3">
                  <button
                    onClick={() => onAcknowledge(alert.alert_id)}
                    className="flex-1 bg-white hover:bg-gray-100 text-gray-900 font-bold py-4 px-6 rounded-xl transition-colors text-lg"
                  >
                    ✓ Acknowledge
                  </button>
                  <button
                    onClick={() => onFocus(alert.swimmer_id)}
                    className="flex-1 bg-black bg-opacity-30 hover:bg-opacity-40 text-white font-bold py-4 px-6 rounded-xl transition-colors text-lg"
                  >
                    👁️ Focus View
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      
      {/* Acknowledged Alerts Summary */}
      {alerts.filter(a => a.acknowledged).length > 0 && (
        <div className="bg-gray-100 rounded-xl p-4">
          <p className="text-sm text-gray-600 text-center">
            ✓ {alerts.filter(a => a.acknowledged).length} alert(s) acknowledged
          </p>
        </div>
      )}
    </div>
  )
}
