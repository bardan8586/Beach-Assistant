/**
 * Video Uploader — drag-and-drop, auto-flows into AI analysis.
 */

import { useCallback, useRef, useState } from 'react'

export type UploadStage = 'idle' | 'selecting' | 'uploading' | 'ready'

interface VideoUploaderProps {
  onVideoSelected: (file: File) => void
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
      if (!file.type.startsWith('video/')) {
        alert('Please select a video file (MP4, MOV, AVI, MKV).')
        return
      }
      if (maxUploadBytes != null && file.size > maxUploadBytes) {
        const mb = Math.max(1, Math.round(maxUploadBytes / (1024 * 1024)))
        alert(`This file is over the ${mb} MB limit. Choose a shorter or more compressed video.`)
        return
      }
      setSelectedFile(file)
      onVideoSelected(file)
    },
    [onVideoSelected, maxUploadBytes],
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
        className={[
          'dash-dropzone relative overflow-hidden rounded-2xl p-8 text-center transition-all sm:p-11',
          busy ? 'cursor-progress' : 'cursor-pointer',
          isDragging ? 'dash-dropzone-active scale-[1.005]' : '',
        ].join(' ')}
        style={{ borderRadius: 'var(--radius-card)' }}
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
          <div className="space-y-5 animate-fade-in">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-600 text-white shadow-lg ring-4 ring-sky-500/15">
              <svg className="h-7 w-7 opacity-95" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="text-lg font-semibold tracking-tight text-slate-100">Upload patrol video</p>
              <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-400">
                Drag and drop or browse. Formats: MP4, MOV, AVI, MKV.
                {maxUploadBytes != null ? (
                  <span className="mt-2 block text-xs font-medium text-slate-500">
                    Limit {Math.max(1, Math.round(maxUploadBytes / (1024 * 1024)))} MB per file.
                  </span>
                ) : null}
              </p>
            </div>
            <span className="btn-primary pointer-events-none inline-flex px-6 py-2.5 text-sm shadow-md">
              Choose file
            </span>
          </div>
        )}

        {selectedFile && (
          <div className="space-y-4 animate-fade-in">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800/80 ring-1 ring-slate-600/60">
              {busy ? (
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" aria-hidden />
              ) : (
                <span className="text-xs font-bold uppercase tracking-wide text-emerald-400">Ready</span>
              )}
            </div>
            <div>
              <p className="break-all text-base font-semibold text-slate-100 sm:text-lg">{selectedFile.name}</p>
              <p className="mt-1 text-sm text-slate-400">
                {formatBytes(selectedFile.size)}
                {statusMessage ? ` · ${statusMessage}` : ''}
              </p>
            </div>

            {busy && (
              <div className="mx-auto max-w-md space-y-2">
                <div
                  className="h-2 w-full overflow-hidden rounded-full bg-slate-700/90"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={uploadProgress}
                >
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-sky-500 to-cyan-500 transition-all"
                    style={{ width: `${Math.max(3, uploadProgress)}%` }}
                  />
                </div>
                <p className="text-xs font-medium tabular-nums text-slate-400">Uploading {uploadProgress}%</p>
              </div>
            )}

            {!busy && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  openPicker()
                }}
                className="btn-secondary text-sm font-semibold"
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
