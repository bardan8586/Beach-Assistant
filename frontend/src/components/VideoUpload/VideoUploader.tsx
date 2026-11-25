/**
 * Video Uploader — drag-and-drop, auto-flows into AI analysis.
 */

import { useCallback, useRef, useState } from 'react'

export type UploadStage = 'idle' | 'selecting' | 'uploading' | 'ready'

interface VideoUploaderProps {
  onVideoSelected: (file: File) => void
  /** Shown in the page error banner instead of a browser alert. */
  onReject?: (message: string) => void
  uploadProgress?: number      // 0-100, driven by parent during upload
  stage?: UploadStage          // external state (set by parent App)
  statusMessage?: string       // short sublabel e.g. "Uploading 42%"
  /** From GET /api/video/limits — client-side guard before upload */
  maxUploadBytes?: number | null
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

export default function VideoUploader({
  onVideoSelected,
  onReject,
  uploadProgress = 0,
  stage = 'idle',
  statusMessage,
  maxUploadBytes = null,
}: VideoUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return
      const reject = (message: string) => {
        if (onReject) onReject(message)
        else window.alert(message)
      }
      if (file.type && !file.type.startsWith('video/') && file.type !== 'application/octet-stream') {
        reject('Choose a video file (MP4, MOV, AVI, MKV, or WebM).')
        return
      }
      if (maxUploadBytes != null && file.size > maxUploadBytes) {
        const mb = Math.max(1, Math.round(maxUploadBytes / (1024 * 1024)))
        reject(`This file is over the ${mb} MB limit. Choose a shorter or more compressed video.`)
        return
      }
      setSelectedFile(file)
      onVideoSelected(file)
    },
    [onVideoSelected, onReject, maxUploadBytes],
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0])
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (stage === 'uploading') return
    handleFile(e.dataTransfer.files?.[0])
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (stage === 'uploading') return
    setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const openPicker = () => inputRef.current?.click()

  const busy = stage === 'uploading'

  return (
    <div className="w-full">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload video for AI analysis"
        onClick={!busy ? openPicker : undefined}
        onKeyDown={(e) => {
          if (busy) return
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            openPicker()
          }
        }}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className="drop"
        style={isDragging ? { borderColor: 'var(--accent)' } : undefined}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          onChange={handleFileInput}
          className="hidden"
          disabled={busy}
        />

        {!selectedFile && (
          <div>
            <p className="kicker">Upload</p>
            <h3>Drop a patrol clip</h3>
            <p className="meta" style={{ maxWidth: 420, margin: '0 auto' }}>
              MP4, MOV, AVI, MKV, or WebM.
              {maxUploadBytes != null ? ` Limit ${Math.max(1, Math.round(maxUploadBytes / (1024 * 1024)))} MB.` : ''}
            </p>
            <span className="btn" style={{ marginTop: 16 }}>Choose file</span>
            {busy && statusMessage ? <p className="meta" style={{ marginTop: 12 }}>{statusMessage}</p> : null}
          </div>
        )}

        {selectedFile && (
          <div>
            <h3>{selectedFile.name}</h3>
            <p className="meta">
              {formatBytes(selectedFile.size)}
              {statusMessage ? ` · ${statusMessage}` : ''}
            </p>

            {busy && (
              <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={uploadProgress} style={{ marginTop: 12 }}>
                <span style={{ width: `${Math.max(4, uploadProgress)}%` }} />
              </div>
            )}

            {!busy && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  openPicker()
                }}
                className="btn-ghost"
                style={{ marginTop: 12 }}
              >
                Replace file
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
