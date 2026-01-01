/**
 * Video Player Component
 * ======================
 * Display video feed with bounding boxes and heatmap overlay
 */

import { useRef, useEffect, useState } from 'react'
import type { Swimmer } from '../../types/swimmer'
import { TRACK_COLORS } from '../../utils/constants'

interface VideoPlayerProps {
  swimmers: Swimmer[]
  showBoundingBoxes: boolean
  showHeatmap: boolean
  cameraId: string
  videoUrl?: string  // Optional video URL to display
}

export default function VideoPlayer({ 
  swimmers,
  showBoundingBoxes,
  showHeatmap,
  cameraId,
  videoUrl
}: VideoPlayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [videoSize, setVideoSize] = useState({ width: 1280, height: 720 })

  // Update video size when video loads
  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    
    const updateSize = () => {
      if (video.videoWidth && video.videoHeight) {
        setVideoSize({ width: video.videoWidth, height: video.videoHeight })
      }
    }
    video.addEventListener('loadedmetadata', updateSize)
    updateSize() // Initial size
    return () => {
      video.removeEventListener('loadedmetadata', updateSize)
    }
  }, [videoUrl])

  // Draw bounding boxes on canvas overlay
  useEffect(() => {
    if (!showBoundingBoxes || !canvasRef.current || !videoRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Match canvas size to video display size
    const container = containerRef.current
    if (container) {
      const rect = container.getBoundingClientRect()
      canvas.width = rect.width
      canvas.height = rect.height
    }

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Calculate scaling factors (video might be displayed at different size)
    const scaleX = canvas.width / videoSize.width
    const scaleY = canvas.height / videoSize.height

    // Draw bounding boxes for each swimmer
    swimmers.forEach((swimmer) => {
      const { x1, y1, x2, y2 } = swimmer.bbox
      const color = TRACK_COLORS[swimmer.track_id % TRACK_COLORS.length]

      // Scale coordinates to canvas size
      const scaledX1 = x1 * scaleX
      const scaledY1 = y1 * scaleY
      const scaledX2 = x2 * scaleX
      const scaledY2 = y2 * scaleY
      const boxWidth = scaledX2 - scaledX1
      const boxHeight = scaledY2 - scaledY1

      // Draw box
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(scaledX1, scaledY1, boxWidth, boxHeight)

      // Draw label background
      const labelWidth = 100
      const labelHeight = 25
      ctx.fillStyle = color
      ctx.fillRect(scaledX1, scaledY1 - labelHeight, labelWidth, labelHeight)

      // Draw label text
      ctx.fillStyle = 'white'
      ctx.font = 'bold 14px Arial'
      ctx.fillText(`ID: ${swimmer.track_id}`, scaledX1 + 5, scaledY1 - 7)
      
      // Draw confidence if available
      if (swimmer.confidence) {
        ctx.font = '12px Arial'
        ctx.fillText(`${(swimmer.confidence * 100).toFixed(0)}%`, scaledX1 + 5, scaledY1 - 25)
      }
    })
  }, [swimmers, showBoundingBoxes, videoSize])

  return (
    <div ref={containerRef} className="relative bg-gray-900 rounded-lg overflow-hidden aspect-video">
      {/* Video Element */}
      {videoUrl ? (
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          autoPlay
          loop
          muted
          playsInline
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-white">
            <div className="text-6xl mb-4">📹</div>
            <p className="text-xl font-medium">Camera {cameraId}</p>
            <p className="text-sm text-gray-400 mt-2">
              {swimmers.length > 0 
                ? `Tracking ${swimmers.length} swimmers` 
                : 'Waiting for video stream...'}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Backend: http://localhost:8000
            </p>
          </div>
        </div>
      )}

      {/* Canvas overlay for bounding boxes */}
      {showBoundingBoxes && (
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ zIndex: 10 }}
        />
      )}

      {/* Swimmer count overlay */}
      {swimmers.length > 0 && (
        <div className="absolute top-4 left-4 bg-black bg-opacity-70 rounded px-3 py-2 z-20">
          <p className="text-white text-sm font-medium">
            🏊 Active Swimmers: {swimmers.length}
          </p>
        </div>
      )}

      {/* Controls overlay */}
      <div className="absolute bottom-4 right-4 flex space-x-2 z-20">
        <button 
          className={`px-3 py-1 rounded text-xs font-medium ${
            showBoundingBoxes 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-800 text-gray-300'
          }`}
        >
          Boxes
        </button>
        <button 
          className={`px-3 py-1 rounded text-xs font-medium ${
            showHeatmap 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-800 text-gray-300'
          }`}
        >
          Heatmap
        </button>
      </div>
    </div>
  )
}
