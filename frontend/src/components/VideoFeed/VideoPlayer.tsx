/**
 * Video Player Component
 * ======================
 * Display video feed with PIXEL-PERFECT bounding boxes and TIMESTAMP-SYNCED overlays
 * 
 * KEY FEATURES:
 * - Uses FrameResult schema for accurate coordinate mapping
 * - Timestamp-based frame selection (not event-based)
 * - Exact scaling from video coordinates to canvas coordinates
 * - Risk-based color coding for lifeguard visibility
 */

import { useRef, useEffect, useState, useMemo } from 'react'
import type { FrameResult, SwimmerData } from '../../types/frameResult'
import { API_BASE_URL } from '../../utils/constants'

// Risk-based colors for lifeguard decision-making
const RISK_COLORS = {
  low: '#10B981',      // Green - Safe
  medium: '#F59E0B',   // Amber - Caution
  high: '#EF4444',     // Red - Alert
  critical: '#DC2626', // Dark Red - Emergency
}

interface VideoPlayerProps {
  frameResults: FrameResult[]  // Pre-processed frame data
  showBoundingBoxes: boolean
  showHeatmap: boolean
  showZones: boolean  // New: Show water zones
  cameraId: string
  videoUrl?: string
  onToggleBoxes?: () => void
  onToggleHeatmap?: () => void
  onToggleZones?: () => void
}

export default function VideoPlayer({ 
  frameResults,
  showBoundingBoxes,
  showHeatmap,
  showZones,
  cameraId,
  videoUrl,
  onToggleBoxes,
  onToggleHeatmap,
  onToggleZones
}: VideoPlayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const animationFrameRef = useRef<number | null>(null)
  
  // Current frame result (timestamp-synced)
  const [currentFrameResult, setCurrentFrameResult] = useState<FrameResult | null>(null)

  // Video dimensions from FrameResult (source of truth) — derived to avoid setState in effect
  const videoDimensions = useMemo(() => {
    if (frameResults.length > 0) {
      const first = frameResults[0]
      return { width: first.video_width, height: first.video_height }
    }
    return { width: 1280, height: 720 }
  }, [frameResults])

  // 🎯 FRAME SYNC: video time (timestamp_ms) or frame_index fallback so overlays match video
  useEffect(() => {
    const video = videoRef.current
    if (!video || frameResults.length === 0) return

    const syncFrameToVideoTime = () => {
      const currentTimeMs = video.currentTime * 1000
      const durationMs = (video.duration || 0) * 1000
      const maxFrameIndex = Math.max(...frameResults.map((f) => f.frame_index))

      // Use timestamp sync only if timestamps look like video time (0..duration), not Unix
      const useTimestampSync =
        frameResults[0].timestamp_ms < 1e10 && frameResults[frameResults.length - 1].timestamp_ms < 1e10

      let closestFrame: FrameResult | null = null

      if (useTimestampSync && durationMs > 0) {
        let minDiff = Infinity
        for (const frame of frameResults) {
          const diff = Math.abs(frame.timestamp_ms - currentTimeMs)
          if (diff < minDiff) {
            minDiff = diff
            closestFrame = frame
          }
          if (frame.timestamp_ms > currentTimeMs + 500) break
        }
      } else {
        // Fallback: sync by frame_index (handles wrong/legacy timestamp data)
        const t = durationMs > 0 ? currentTimeMs / durationMs : 0
        const targetIndex = t * maxFrameIndex
        let minDiff = Infinity
        for (const frame of frameResults) {
          const diff = Math.abs(frame.frame_index - targetIndex)
          if (diff < minDiff) {
            minDiff = diff
            closestFrame = frame
          }
        }
      }

      const sameFrame =
        currentFrameResult &&
        closestFrame &&
        currentFrameResult.frame_index === closestFrame.frame_index
      if (closestFrame && !sameFrame) {
        setCurrentFrameResult(closestFrame)
      }

      animationFrameRef.current = requestAnimationFrame(syncFrameToVideoTime)
    }

    animationFrameRef.current = requestAnimationFrame(syncFrameToVideoTime)
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [frameResults, currentFrameResult])

  // 🎨 PIXEL-PERFECT RENDERING (Task 1.4)
  // Draws bounding boxes with exact coordinate mapping
  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Match canvas size to container
    const rect = container.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // No frame data yet
    if (!currentFrameResult) return

    // 🔑 CRITICAL: Calculate scaling from VIDEO coordinates to CANVAS coordinates
    // videoDimensions = original AI processing resolution (from FrameResult)
    // canvas.width/height = current display size
    const scaleX = canvas.width / videoDimensions.width
    const scaleY = canvas.height / videoDimensions.height

    // Draw water zones if enabled (use scene from FrameResult)
    const scene = currentFrameResult.scene
    const shoreYpx = scene?.shore_line_y ?? null
    if (showZones && scene && shoreYpx != null) {
      const horizonYpx = scene.horizon_y ?? 0
      // Danger zone (red, transparent) from horizon to shore
      ctx.fillStyle = 'rgba(239, 68, 68, 0.15)'
      ctx.fillRect(0, horizonYpx * scaleY, canvas.width, (shoreYpx - horizonYpx) * scaleY)
      // Shore line
      ctx.strokeStyle = '#10B981'
      ctx.lineWidth = 2
      ctx.setLineDash([10, 5])
      const shoreY = shoreYpx * scaleY
      ctx.beginPath()
      ctx.moveTo(0, shoreY)
      ctx.lineTo(canvas.width, shoreY)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = '#10B981'
      ctx.font = 'bold 12px Arial'
      ctx.fillText('SHORE LINE', 10, shoreY - 5)
    }

    // Draw bounding boxes for each swimmer
    if (showBoundingBoxes && currentFrameResult.swimmers) {
      currentFrameResult.swimmers.forEach((swimmer: SwimmerData) => {
        const { x, y, w, h } = swimmer.bbox
        
        // Get risk-based color
        const color = RISK_COLORS[swimmer.risk_level as keyof typeof RISK_COLORS] || RISK_COLORS.low
        
        // 🎯 PIXEL-PERFECT SCALING
        const scaledX = x * scaleX
        const scaledY = y * scaleY
        const scaledW = w * scaleX
        const scaledH = h * scaleY

        // Draw box with risk-based color
        ctx.strokeStyle = color
        ctx.lineWidth = swimmer.risk_level === 'CRITICAL' ? 4 : swimmer.risk_level === 'HIGH' ? 3 : 2
        ctx.strokeRect(scaledX, scaledY, scaledW, scaledH)

        // Draw label background
        const labelText = `ID:${swimmer.track_id} ${swimmer.risk_level.toUpperCase()}`
        ctx.font = 'bold 13px Arial'
        const labelWidth = ctx.measureText(labelText).width + 12
        const labelHeight = 22
        
        ctx.fillStyle = color
        ctx.fillRect(scaledX, scaledY - labelHeight, labelWidth, labelHeight)

        // Draw label text
        ctx.fillStyle = 'white'
        ctx.fillText(labelText, scaledX + 6, scaledY - 6)
        
        // Draw zone indicator
        ctx.font = '11px Arial'
        ctx.fillStyle = color
        ctx.fillText(`${swimmer.zone} | Risk:${swimmer.risk_score.toFixed(0)}`, scaledX, scaledY + scaledH + 14)
      })
    }

    // Draw frame info overlay
    if (currentFrameResult) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
      ctx.fillRect(canvas.width - 200, 10, 190, 60)
      ctx.fillStyle = 'white'
      ctx.font = '11px monospace'
      ctx.fillText(`Frame: ${currentFrameResult.frame_index}`, canvas.width - 190, 25)
      ctx.fillText(`Time: ${(currentFrameResult.timestamp_ms / 1000).toFixed(2)}s`, canvas.width - 190, 40)
      ctx.fillText(`Swimmers: ${currentFrameResult.swimmers?.length || 0}`, canvas.width - 190, 55)
    }
    
  }, [currentFrameResult, showBoundingBoxes, showZones, showHeatmap, videoDimensions])

  const swimmerCount = currentFrameResult?.swimmers?.length ?? 0
  const activeAlerts = currentFrameResult?.alerts?.length ?? 0

  return (
    <div
      ref={containerRef}
      className="relative overflow-hidden aspect-video rounded-lg bg-slate-900"
      style={{ borderRadius: 'var(--radius-card)' }}
    >
      {/* Video Element */}
      {videoUrl ? (
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          controls
          playsInline
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-white">
            <div className="text-6xl mb-4">📹</div>
            <p className="text-xl font-medium">Camera {cameraId}</p>
            <p className="text-sm text-gray-400 mt-2">
              {frameResults.length > 0
                ? `${frameResults.length} frames loaded` 
                : 'Waiting for video stream...'}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              API: {API_BASE_URL}
            </p>
          </div>
        </div>
      )}

      {/* Canvas overlay - ALWAYS rendered for pixel-perfect sync */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ zIndex: 10 }}
      />

      {/* Swimmer count overlay */}
      <div className="absolute top-3 left-3 z-20 space-y-1 rounded-lg bg-black/80 px-3 py-2 backdrop-blur-sm" style={{ borderRadius: 'var(--radius-button)' }}>
        <p className="text-sm font-semibold text-white">🏊 Swimmers: {swimmerCount}</p>
        {activeAlerts > 0 && (
          <p className="text-xs font-medium text-red-400 animate-pulse">⚠️ {activeAlerts} Active Alert{activeAlerts > 1 ? 's' : ''}</p>
        )}
        {currentFrameResult && (
          <p className="text-xs text-slate-400">Frame {currentFrameResult.frame_index} · {(currentFrameResult.timestamp_ms / 1000).toFixed(1)}s</p>
        )}
      </div>

      {/* Controls overlay */}
      {(onToggleBoxes || onToggleHeatmap || onToggleZones) && (
        <div className="absolute bottom-3 right-3 z-20 flex gap-2">
          {onToggleBoxes && (
            <button
              onClick={onToggleBoxes}
              className={`px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${showBoundingBoxes ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
              style={{ borderRadius: 'var(--radius-button)' }}
            >
              {showBoundingBoxes ? '✓ ' : ''}Boxes
            </button>
          )}
          {onToggleZones && (
            <button
              onClick={onToggleZones}
              className={`px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${showZones ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
              style={{ borderRadius: 'var(--radius-button)' }}
            >
              {showZones ? '✓ ' : ''}Zones
            </button>
          )}
          {onToggleHeatmap && (
            <button
              onClick={onToggleHeatmap}
              className={`px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${showHeatmap ? 'bg-violet-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
              style={{ borderRadius: 'var(--radius-button)' }}
            >
              {showHeatmap ? '✓ ' : ''}Heatmap
            </button>
          )}
        </div>
      )}

      {/* Water conditions (from scene) */}
      {currentFrameResult?.scene && (
        <div className="absolute top-3 right-3 z-20 rounded-lg border border-slate-600 bg-black/80 px-3 py-2 backdrop-blur-sm" style={{ borderRadius: 'var(--radius-button)' }}>
          <p className="mb-1 text-xs font-medium text-white">Water conditions</p>
          <div className="text-xs space-y-0.5 text-slate-300">
            {currentFrameResult.scene.visibility != null && (
              <div className="flex justify-between gap-4">
                <span>Visibility</span>
                <span className="font-medium text-white">
                  {((currentFrameResult.scene.visibility ?? 0) * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {currentFrameResult.scene.calm_score != null && (
              <div className="flex justify-between gap-4">
                <span>Calm</span>
                <span className="font-medium text-white">
                  {((currentFrameResult.scene.calm_score ?? 0) * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
