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
      case 'emergency':
        return { bg: 'bg-red-600', border: 'border-red-500/90', text: 'text-red-950', badge: 'EMERGENCY' }
      case 'alert':
        return { bg: 'bg-orange-600', border: 'border-orange-400/90', text: 'text-orange-950', badge: 'ALERT' }
      case 'watch':
        return { bg: 'bg-amber-500', border: 'border-amber-400/90', text: 'text-amber-950', badge: 'WATCH' }
      default:
        return { bg: 'bg-slate-500', border: 'border-slate-400', text: 'text-slate-950', badge: 'INFO' }
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
      <section className="card card-elevated p-8 text-center sm:p-10 cc-enter" aria-label="Priority alerts">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15 ring-1 ring-emerald-400/30">
          <span className="text-lg font-bold text-emerald-300">OK</span>
        </div>
        <h2 className="text-xl font-semibold text-slate-100">No open priority alerts</h2>
        <p className="mt-2 text-sm text-slate-400">Highest-severity items will surface here automatically.</p>
        <p className="mt-4 text-xs text-slate-500">
          {alerts.length > 0 ? `${alerts.length} stored alert(s) (incl. acknowledged)` : 'Monitoring active feed'}
        </p>
      </section>
    )
  }

  return (
    <div className="space-y-5">
      <div className="card card-elevated flex flex-wrap items-center justify-between gap-4 p-4 sm:p-5 cc-enter">
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
          </span>
          <div>
            <p className="card-title">Queue</p>
            <h2 className="card-title-lg">Priority alerts</h2>
          </div>
        </div>
        <div className="flex flex-wrap gap-3 text-xs font-semibold sm:text-sm">
          <span className="rounded-lg border border-red-500/35 bg-red-950/50 px-2.5 py-1 text-red-100">
            E {alerts.filter((a) => a.level === 'emergency' && !a.acknowledged).length}
          </span>
          <span className="rounded-lg border border-orange-500/35 bg-orange-950/45 px-2.5 py-1 text-orange-100">
            A {alerts.filter((a) => a.level === 'alert' && !a.acknowledged).length}
          </span>
          <span className="rounded-lg border border-amber-500/35 bg-amber-950/40 px-2.5 py-1 text-amber-100">
            W {alerts.filter((a) => a.level === 'watch' && !a.acknowledged).length}
          </span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 gap-4">
        {topAlerts.map((alert) => {
          const colors = getLevelColor(alert.level)
          const isEmergency = alert.level === 'emergency'

          return (
            <div
              key={alert.alert_id}
              className={`
                ${colors.bg} ${isEmergency ? 'animate-pulse-slow' : ''}
                overflow-hidden rounded-2xl border-2 shadow-lg transition-shadow hover:shadow-xl
                ${colors.border}
              `}
            >
              <div className="p-5 sm:p-6">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-md bg-white/95 px-2 py-0.5 text-[10px] font-bold tracking-widest text-slate-800">
                        {colors.badge}
                      </span>
                      <h3 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Track {alert.swimmer_id}</h3>
                    </div>
                    <p className="mt-2 text-sm font-medium text-white/95 sm:text-base">
                      {alert.zone.toUpperCase()} · {alert.duration.toFixed(0)}s · confidence {(alert.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="shrink-0 rounded-xl border border-white/25 bg-black/10 px-4 py-2 text-right backdrop-blur-sm">
                    <div className="text-2xl font-bold tabular-nums text-white sm:text-3xl">{alert.risk_score.toFixed(0)}</div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-white/80">Risk</div>
                  </div>
                </div>

                <div className="mb-4 rounded-xl border border-white/20 bg-black/10 p-4 backdrop-blur-sm">
                  <p className="text-sm font-medium leading-relaxed text-white sm:text-base">{alert.context}</p>
                </div>

                <div className="mb-4 rounded-xl bg-white p-4 shadow-inner">
                  <p className={`text-base font-semibold leading-snug sm:text-lg ${colors.text}`}>{alert.action_recommended}</p>
                  <p className="mt-2 font-mono text-xs text-slate-500">
                    Loc {alert.location[0]}, {alert.location[1]}
                  </p>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
                  <button
                    type="button"
                    onClick={() => onAcknowledge(alert.alert_id)}
                    className="btn-secondary flex-1 py-3.5 text-base font-semibold"
                  >
                    Acknowledge
                  </button>
                  <button
                    type="button"
                    onClick={() => onFocus(alert.swimmer_id)}
                    className="flex-1 rounded-xl border border-white/30 bg-black/25 py-3.5 text-base font-semibold text-white backdrop-blur-sm transition hover:bg-black/35"
                  >
                    Focus on video
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      
      {/* Acknowledged Alerts Summary */}
      {alerts.filter((a) => a.acknowledged).length > 0 && (
        <div className="card card-elevated p-4 text-center">
          <p className="text-sm text-slate-400">
            {alerts.filter((a) => a.acknowledged).length} acknowledged alert(s) on file
          </p>
        </div>
      )}
    </div>
  )
}
