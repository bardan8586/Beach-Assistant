/**
 * Header — compact brand bar + live status.
 */

import { useState, useEffect } from 'react'

interface HeaderProps {
  selectedCamera: string
  isConnected: boolean
  processingStatus?: string
  frameCount?: number
}

export default function Header({ selectedCamera, isConnected, processingStatus, frameCount = 0 }: HeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const statusLabel = isConnected ? 'Live' : 'Offline'
  const statusAria = isConnected ? 'System connected' : 'System disconnected'
  const hasLiveData = frameCount > 0

  return (
    <header
      className="relative border-b border-cyan-950/20 text-white shadow-md"
      style={{
        background: 'linear-gradient(105deg, rgb(8 47 73) 0%, rgb(12 74 110) 42%, rgb(14 116 144) 100%)',
      }}
      role="banner"
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.12]"
        style={{
          backgroundImage: 'radial-gradient(circle at 20% 0%, white, transparent 55%)',
        }}
        aria-hidden
      />
      <div className="relative mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-4 px-4 py-3.5 sm:px-8">
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/20 bg-white/10 text-sm font-bold tracking-tight text-white shadow-inner backdrop-blur-sm sm:h-11 sm:w-11"
            aria-hidden
          >
            BS
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold tracking-tight text-white sm:text-lg">
              Beach Safety Monitor
            </h1>
            <p className="truncate text-xs text-cyan-100/85 sm:text-[13px]">
              Lifeguard decision support · AI-assisted only — not a substitute for direct supervision
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 sm:gap-4">
          <div
            className="flex items-center gap-2 rounded-full border border-white/15 bg-black/10 px-3 py-1.5 backdrop-blur-sm"
            aria-live="polite"
            aria-label={statusAria}
          >
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${isConnected ? 'bg-emerald-400 shadow-[0_0_8px_rgb(52_211_153)]' : 'bg-red-400'}`}
            />
            <span className="text-xs font-semibold text-white sm:text-sm">{statusLabel}</span>
            {hasLiveData && (
              <span className="hidden border-l border-white/25 pl-2 text-[11px] font-medium text-cyan-100 sm:inline">
                {frameCount} frames
              </span>
            )}
          </div>

          {processingStatus && processingStatus !== 'idle' && (
            <span className="status-pill border border-white/20 bg-white/10 text-cyan-50">
              {processingStatus === 'uploading' && 'Uploading'}
              {processingStatus === 'processing' && 'Analyzing'}
              {processingStatus === 'completed' && 'Ready'}
              {processingStatus === 'error' && 'Error'}
            </span>
          )}

          <div className="hidden h-8 w-px bg-white/15 sm:block" aria-hidden />

          <div className="text-right">
            <div className="text-[10px] font-medium uppercase tracking-wider text-cyan-200/80">Feed</div>
            <div className="max-w-[200px] truncate font-mono text-xs text-white sm:max-w-xs sm:text-sm">
              {selectedCamera}
            </div>
          </div>

          <time
            className="tabular-nums text-xs font-medium text-cyan-100/90 sm:text-sm"
            dateTime={currentTime.toISOString()}
          >
            {currentTime.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </time>
        </div>
      </div>
    </header>
  )
}
