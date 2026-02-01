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
  /** Number of frame results received (for "Live" indicator) */
  frameCount?: number
}

export default function Header({ selectedCamera, isConnected, processingStatus, frameCount = 0 }: HeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const statusLabel = isConnected ? 'Operational' : 'Disconnected'
  const statusAria = isConnected ? 'System operational' : 'System disconnected'
  const hasLiveData = frameCount > 0

  return (
    <header
      className="text-white shadow-sm border-b border-slate-600/80"
      style={{ backgroundColor: 'rgb(var(--color-surface-header))' }}
      role="banner"
    >
      <div className="container mx-auto max-w-[1600px] px-4 sm:px-6 py-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <span className="text-2xl select-none" aria-hidden="true">🏖️</span>
            <div>
              <h1 className="text-lg sm:text-xl font-semibold text-white tracking-tight">
                Beach Safety — Lifeguard Decision Support
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                AI-assisted swimmer monitoring · Not a substitute for direct supervision
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
              <span className="text-sm font-medium text-slate-200">{statusLabel}</span>
              {isConnected && (
                <span className="text-xs text-slate-400" title="Backend connection">· Backend connected</span>
              )}
              {hasLiveData && (
                <span className="text-xs font-medium text-emerald-400" title="Receiving frame data">· Receiving frames</span>
              )}
            </div>
            {processingStatus && processingStatus !== 'idle' && (
              <span className="status-pill bg-slate-600 text-slate-200">
                {processingStatus === 'uploading' && 'Uploading…'}
                {processingStatus === 'processing' && 'Processing…'}
                {processingStatus === 'completed' && 'Ready'}
                {processingStatus === 'error' && 'Error'}
              </span>
            )}
            <div className="text-sm text-slate-400">
              <span className="text-slate-500">Feed</span>{' '}
              <span className="font-mono text-slate-300">{selectedCamera}</span>
            </div>
            <time
              className="text-sm text-slate-400 font-mono tabular-nums"
              dateTime={currentTime.toISOString()}
            >
              {currentTime.toLocaleTimeString()}
            </time>
          </div>
        </div>
      </div>
    </header>
  )
}


