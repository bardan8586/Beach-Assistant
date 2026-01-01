/**
 * Video Processor Component
 * ==========================
 * Process video and display results
 */

import { useState, useEffect } from 'react'
import VideoPlayer from './VideoPlayer'
import { useAppStore } from '../../store/useAppStore'

interface ProcessingStats {
  framesProcessed: number
  fps: number
  swimmersDetected: number
  processing: boolean
}

interface VideoProcessorProps {
  videoFile: File | null
}

export default function VideoProcessor({ videoFile }: VideoProcessorProps) {
  const [stats, setStats] = useState<ProcessingStats>({
    framesProcessed: 0,
    fps: 0,
    swimmersDetected: 0,
    processing: false,
  })
  const [videoUrl, setVideoUrl] = useState<string>('')

  useEffect(() => {
    if (videoFile) {
      const url = URL.createObjectURL(videoFile)
      setVideoUrl(url)
      return () => URL.revokeObjectURL(url)
    }
  }, [videoFile])

  const startProcessing = () => {
    setStats(prev => ({ ...prev, processing: true }))
    
    // Simulate processing (in real app, this would call AI pipeline)
    let frames = 0
    const interval = setInterval(() => {
      frames += 10
      setStats({
        framesProcessed: frames,
        fps: 10,
        swimmersDetected: Math.floor(Math.random() * 5),
        processing: frames < 300,
      })
      
      if (frames >= 300) {
        clearInterval(interval)
      }
    }, 1000)
  }

  if (!videoFile) {
    return (
      <div className="text-center py-12 text-gray-500">
        <div className="text-6xl mb-4">📹</div>
        <p className="text-lg">No video selected</p>
        <p className="text-sm mt-2">Upload a video to start processing</p>
      </div>
    )
  }

  const { swimmers, showBoundingBoxes, showHeatmap } = useAppStore()

  return (
    <div className="space-y-4">
      {/* Video Preview with Overlays */}
      <VideoPlayer
        swimmers={swimmers}
        showBoundingBoxes={showBoundingBoxes}
        showHeatmap={showHeatmap}
        cameraId="uploaded_video"
        videoUrl={videoUrl}
      />

      {/* Processing Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">
            {stats.framesProcessed}
          </div>
          <div className="text-sm text-gray-600">Frames Processed</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">{stats.fps}</div>
          <div className="text-sm text-gray-600">FPS</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-primary-600">
            {stats.swimmersDetected}
          </div>
          <div className="text-sm text-gray-600">Swimmers Detected</div>
        </div>
      </div>

      {/* Process Button */}
      {!stats.processing && stats.framesProcessed === 0 && (
        <button
          onClick={startProcessing}
          className="w-full py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
        >
          🚀 Start AI Processing
        </button>
      )}

      {stats.processing && (
        <div className="text-center py-3 bg-blue-50 rounded-lg">
          <div className="flex items-center justify-center space-x-2">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
            <span className="text-blue-700 font-medium">Processing video...</span>
          </div>
        </div>
      )}

      {!stats.processing && stats.framesProcessed > 0 && (
        <div className="text-center py-3 bg-green-50 rounded-lg">
          <span className="text-green-700 font-medium">
            ✅ Processing complete! {stats.framesProcessed} frames analyzed
          </span>
        </div>
      )}
    </div>
  )
}

