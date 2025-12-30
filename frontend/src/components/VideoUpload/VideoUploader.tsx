/**
 * Video Uploader Component
 * =========================
 * Upload and process videos through AI pipeline
 */

import { useState } from 'react'

interface VideoUploaderProps {
  onVideoSelected: (file: File) => void
}

export default function VideoUploader({ onVideoSelected }: VideoUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file)
      onVideoSelected(file)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file)
      onVideoSelected(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  return (
    <div className="w-full">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="text-6xl mb-4">🎥</div>
        
        {selectedFile ? (
          <div>
            <p className="text-lg font-medium text-gray-900 mb-2">
              ✅ {selectedFile.name}
            </p>
            <p className="text-sm text-gray-600 mb-4">
              Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
            <label className="inline-block px-4 py-2 bg-primary-600 text-white rounded cursor-pointer hover:bg-primary-700">
              Choose Different Video
              <input
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>
          </div>
        ) : (
          <div>
            <p className="text-lg font-medium text-gray-900 mb-2">
              Drop video here or click to upload
            </p>
            <p className="text-sm text-gray-600 mb-4">
              Supports: MP4, AVI, MOV, MKV
            </p>
            <label className="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg cursor-pointer hover:bg-primary-700 transition-colors">
              📁 Select Video File
              <input
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>
          </div>
        )}
      </div>
    </div>
  )
}

