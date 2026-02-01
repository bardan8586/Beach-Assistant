/**
 * Header Component
 * ================
 * Top navigation bar with status indicators — government decision-support grade.
 */

import { useState, useEffect } from 'react'

interface HeaderProps {
  selectedCamera: string
  isConnected: boolean
  processingStatus?: string
}

export default function Header({ selectedCamera, isConnected, processingStatus }: HeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const statusLabel = isConnected ? 'Operational' : 'Disconnected'
  const statusAria = isConnected ? 'System operational' : 'System disconnected'

  return (
    <header className="bg-slate-800 text-white shadow-md border-b border-slate-700" role="banner">
      <div className="px-6 py-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <span className="text-2xl" aria-hidden="true">🏖️</span>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Beach Safety — Lifeguard Decision Support
              </h1>
              <p className="text-xs text-slate-400">
                AI-assisted swimmer monitoring • Not a substitute for direct supervision
              </p>
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2" aria-live="polite" aria-label={statusAria}>
              <div
                className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                  isConnected ? 'bg-emerald-500' : 'bg-red-500'
                } ${isConnected ? 'animate-pulse' : ''}`}
              />
              <span className="text-sm font-medium text-slate-200">
                {statusLabel}
              </span>
            </div>
            {processingStatus && processingStatus !== 'idle' && (
              <span className="text-xs px-2 py-0.5 rounded bg-slate-600 text-slate-200">
                {processingStatus === 'uploading' && 'Uploading…'}
                {processingStatus === 'processing' && 'Processing…'}
                {processingStatus === 'completed' && 'Ready'}
                {processingStatus === 'error' && 'Error'}
              </span>
            )}
            <div className="text-sm text-slate-400">
              <span className="text-slate-500">Feed:</span>{' '}
              <span className="font-mono text-slate-300">{selectedCamera}</span>
            </div>
            <time className="text-sm text-slate-400 font-mono tabular-nums" dateTime={currentTime.toISOString()}>
              {currentTime.toLocaleTimeString()}
            </time>
          </div>
        </div>
      </div>
    </header>
  )
}


