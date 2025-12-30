/**
 * Video Player Component
 * ======================
 * Display video feed with bounding boxes and heatmap overlay
 */

import { useRef, useEffect } from 'react'
import type { Swimmer } from '../../types/swimmer'
import { TRACK_COLORS } from '../../utils/constants'

interface VideoPlayerProps {
  swimmers: Swimmer[]
  showBoundingBoxes: boolean
  showHeatmap: boolean
  cameraId: string
}

export default function VideoPlayer({ 
  swimmers,
  showBoundingBoxes,
  showHeatmap,
  cameraId
}: VideoPlayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Draw bounding boxes on canvas
  useEffect(() => {
    if (!showBoundingBoxes || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw bounding boxes for each swimmer
    swimmers.forEach((swimmer, index) => {
      const { x1, y1, x2, y2 } = swimmer.bbox
      const color = TRACK_COLORS[index % TRACK_COLORS.length]

      // Draw box
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

      // Draw label background
      ctx.fillStyle = color
      ctx.fillRect(x1, y1 - 25, 80, 25)

      // Draw label text
      ctx.fillStyle = 'white'
      ctx.font = 'bold 14px Arial'
      ctx.fillText(`ID: ${swimmer.track_id}`, x1 + 5, y1 - 7)
    })
  }, [swimmers, showBoundingBoxes])

  return (
    <div className="relative bg-gray-900 rounded-lg overflow-hidden aspect-video">
      {/* Video Element (placeholder for now) */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-6xl mb-4">📹</div>
          <p className="text-xl font-medium">Camera {cameraId}</p>
          <p className="text-sm text-gray-400 mt-2">
            Waiting for video stream...
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Backend: http://localhost:8000
          </p>
        </div>
      </div>

      {/* Canvas overlay for bounding boxes */}
      {showBoundingBoxes && (
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
          width={1920}
          height={1080}
        />
      )}

      {/* Swimmer count overlay */}
      {swimmers.length > 0 && (
        <div className="absolute top-4 left-4 bg-black bg-opacity-70 rounded px-3 py-2">
          <p className="text-white text-sm font-medium">
            🏊 Active Swimmers: {swimmers.length}
          </p>
        </div>
      )}

      {/* Controls overlay */}
      <div className="absolute bottom-4 right-4 flex space-x-2">
        <button 
          className={`px-3 py-1 rounded text-xs font-medium ${
            showBoundingBoxes 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-800 text-gray-300'
          }`}
        >
          Bounding Boxes
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

