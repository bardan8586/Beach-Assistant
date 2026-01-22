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

import { useRef, useEffect, useState } from 'react'
import type { FrameResult, SwimmerData } from '../../types/frameResult'

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
  
  // Video dimensions from FrameResult (source of truth!)
  const [videoDimensions, setVideoDimensions] = useState({ width: 1280, height: 720 })

  // Extract video dimensions from first FrameResult
  useEffect(() => {
    if (frameResults.length > 0) {
      const firstFrame = frameResults[0]
      setVideoDimensions({
        width: firstFrame.video_width,
        height: firstFrame.video_height
      })
      console.log(`📐 Video dimensions from FrameResult: ${firstFrame.video_width}x${firstFrame.video_height}`)
    }
  }, [frameResults])

  // 🎯 TIMESTAMP-BASED FRAME SELECTION (Task 1.5)
  // Syncs overlays with video playback time
  useEffect(() => {
    const video = videoRef.current
    if (!video || frameResults.length === 0) return

    const syncFrameToVideoTime = () => {
      const currentTimeMs = video.currentTime * 1000
      
      // Find the closest frame to current video time
      let closestFrame: FrameResult | null = null
      let minDiff = Infinity
      
      for (const frame of frameResults) {
        const diff = Math.abs(frame.timestamp_ms - currentTimeMs)
        if (diff < minDiff) {
          minDiff = diff
          closestFrame = frame
        }
        // Optimize: stop searching if we're past the current time
        if (frame.timestamp_ms > currentTimeMs + 500) break
      }
      
      if (closestFrame && closestFrame !== currentFrameResult) {
        setCurrentFrameResult(closestFrame)
      }
      
      // Continue syncing
      animationFrameRef.current = requestAnimationFrame(syncFrameToVideoTime)
    }
    
    // Start sync loop
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

    console.log(`🎯 Scaling: ${videoDimensions.width}x${videoDimensions.height} → ${canvas.width}x${canvas.height} (${scaleX.toFixed(3)}x, ${scaleY.toFixed(3)}y)`)

    // Draw water zones if enabled
    if (showZones && currentFrameResult.scene_geometry.has_valid_geometry) {
      const geo = currentFrameResult.scene_geometry
      
      // Danger zone (red, transparent)
      ctx.fillStyle = 'rgba(239, 68, 68, 0.15)'
      ctx.fillRect(0, geo.water_start_y * scaleY, canvas.width, (geo.shore_line_y - geo.water_start_y) * scaleY)
      
      // Draw shore line
      ctx.strokeStyle = '#10B981'
      ctx.lineWidth = 2
      ctx.setLineDash([10, 5])
      const shoreY = geo.shore_line_y * scaleY
      ctx.beginPath()
      ctx.moveTo(0, shoreY)
      ctx.lineTo(canvas.width, shoreY)
      ctx.stroke()
      ctx.setLineDash([])
      
      // Shore label
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
        ctx.lineWidth = swimmer.risk_level === 'critical' ? 4 : swimmer.risk_level === 'high' ? 3 : 2
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

  const swimmerCount = currentFrameResult?.swimmers?.length || 0
  const activeAlerts = currentFrameResult?.active_alerts || 0

  return (
    <div ref={containerRef} className="relative bg-gray-900 rounded-lg overflow-hidden aspect-video">
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
              Backend: http://localhost:8000
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
      <div className="absolute top-4 left-4 bg-black bg-opacity-80 rounded-lg px-4 py-2 z-20 space-y-1">
        <p className="text-white text-sm font-bold">
          🏊 Swimmers: {swimmerCount}
        </p>
        {activeAlerts > 0 && (
          <p className="text-red-400 text-xs font-medium animate-pulse">
            ⚠️ {activeAlerts} Active Alert{activeAlerts > 1 ? 's' : ''}
          </p>
        )}
        {currentFrameResult && (
          <p className="text-gray-400 text-xs">
            Frame {currentFrameResult.frame_index} | {(currentFrameResult.timestamp_ms / 1000).toFixed(1)}s
          </p>
        )}
      </div>

      {/* Controls overlay */}
      {(onToggleBoxes || onToggleHeatmap || onToggleZones) && (
        <div className="absolute bottom-4 right-4 flex space-x-2 z-20">
          {onToggleBoxes && (
            <button 
              onClick={onToggleBoxes}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                showBoundingBoxes 
                  ? 'bg-green-600 text-white shadow-lg' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {showBoundingBoxes ? '✓' : ''} Boxes
            </button>
          )}
          {onToggleZones && (
            <button 
              onClick={onToggleZones}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                showZones 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {showZones ? '✓' : ''} Zones
            </button>
          )}
          {onToggleHeatmap && (
            <button 
              onClick={onToggleHeatmap}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                showHeatmap 
                  ? 'bg-purple-600 text-white shadow-lg' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {showHeatmap ? '✓' : ''} Heatmap
            </button>
          )}
        </div>
      )}

      {/* Water conditions indicator */}
      {currentFrameResult?.water_conditions && (
        <div className="absolute top-4 right-4 bg-black bg-opacity-80 rounded-lg px-3 py-2 z-20">
          <p className="text-white text-xs font-medium mb-1">🌊 Water</p>
          <div className="text-xs space-y-0.5">
            <div className="flex items-center space-x-2">
              <span className="text-gray-400">Visibility:</span>
              <span className="text-white font-medium">
                {(currentFrameResult.water_conditions.visibility * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-gray-400">Calm:</span>
              <span className="text-white font-medium">
                {(currentFrameResult.water_conditions.calm_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
