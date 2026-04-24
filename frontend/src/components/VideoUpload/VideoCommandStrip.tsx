/**
 * Always-visible clip control — compact operational strip (add / change video).
 * Uses the same file → parent callback flow as VideoUploader; does not replace it.
 */

import { useRef } from 'react'

export interface VideoCommandStripProps {
  uploadedVideo: File | null
  uploadProgress: number
  processingStatus: string
  processing: boolean
  maxUploadBytes: number | null
  onVideoFile: (file: File) => void
  onResetUpload: () => void
}

function formatMaxMb(bytes: number | null): string | null {
  if (bytes == null) return null
  return `${Math.max(1, Math.round(bytes / (1024 * 1024)))} MB max`
}

function pipelineLabel(
  uploadedVideo: File | null,
  processingStatus: string,
  processing: boolean,
  uploadProgress: number,
): { label: string; tone: 'neutral' | 'busy' | 'live' | 'warn' | 'ok' } {
  if (processingStatus === 'error') return { label: 'Error', tone: 'warn' }
  if (processingStatus === 'uploading') return { label: `Uploading ${uploadProgress}%`, tone: 'busy' }
  if (processing) return { label: 'Analyzing', tone: 'live' }
  if (processingStatus === 'completed' && uploadedVideo) return { label: 'Ready', tone: 'ok' }
  if (uploadedVideo && processingStatus === 'idle') return { label: 'Clip loaded', tone: 'neutral' }
  return { label: 'No clip', tone: 'neutral' }
}

export default function VideoCommandStrip({
  uploadedVideo,
  uploadProgress,
  processingStatus,
  processing,
  maxUploadBytes,
  onVideoFile,
  onResetUpload,
}: VideoCommandStripProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const busy = processing || processingStatus === 'uploading'
  const { label, tone } = pipelineLabel(uploadedVideo, processingStatus, processing, uploadProgress)

  const openPicker = () => {
    if (busy) return
    inputRef.current?.click()
  }

  /** Reset workspace then open picker — same as in-card “New video” flow. */
  const changeClip = () => {
    if (busy) return
    onResetUpload()
    queueMicrotask(() => inputRef.current?.click())
  }

  const toneClass =
    tone === 'live'
      ? 'border-cyan-500/40 bg-cyan-500/15 text-cyan-100'
      : tone === 'busy'
        ? 'border-sky-500/35 bg-sky-500/10 text-sky-100'
        : tone === 'warn'
          ? 'border-red-500/40 bg-red-950/40 text-red-100'
          : tone === 'ok'
            ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-100'
            : 'border-slate-600/80 bg-slate-800/60 text-slate-300'

  return (
    <div
      className="cc-upload-strip sticky top-0 z-40 border-b border-slate-700/80 transition-colors duration-200"
      role="region"
      aria-label="Video clip"
    >
      <div className="mx-auto flex max-w-[1680px] flex-wrap items-center gap-3 px-4 py-2.5 sm:px-8 sm:py-3">
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) onVideoFile(f)
            e.target.value = ''
          }}
        />

        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Clip</p>
            <p className="truncate font-mono text-xs text-slate-200 sm:text-sm" title={uploadedVideo?.name ?? undefined}>
              {uploadedVideo ? uploadedVideo.name : 'No patrol video loaded'}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <span className={`status-pill border px-2.5 py-1 ${toneClass}`}>{label}</span>
          {formatMaxMb(maxUploadBytes) ? (
            <span className="hidden text-[11px] text-slate-500 sm:inline">{formatMaxMb(maxUploadBytes)}</span>
          ) : null}
        </div>

        <div className="flex w-full shrink-0 gap-2 sm:ml-auto sm:w-auto">
          {!uploadedVideo ? (
            <button type="button" disabled={busy} onClick={openPicker} className="btn-primary px-4 py-2 text-xs sm:text-sm">
              Add clip
            </button>
          ) : (
            <button type="button" disabled={busy} onClick={changeClip} className="btn-secondary px-4 py-2 text-xs sm:text-sm">
              Change clip
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
