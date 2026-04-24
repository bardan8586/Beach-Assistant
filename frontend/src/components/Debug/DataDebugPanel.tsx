/**
 * Developer diagnostics — tucked away, same visual language as the app.
 */

import { useState } from 'react'
import type { Swimmer } from '../../types/swimmer'

interface DataDebugPanelProps {
  swimmers: Swimmer[]
  isConnected: boolean
  selectedCamera?: string
}

export default function DataDebugPanel({ swimmers, isConnected, selectedCamera }: DataDebugPanelProps) {
  const [isOpen, setIsOpen] = useState(false)

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-5 right-5 z-50 rounded-full border border-slate-600/90 bg-slate-900/90 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-300 shadow-lg backdrop-blur-sm transition hover:border-slate-500 hover:text-white"
      >
        Debug
      </button>
    )
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex w-[min(100vw-2rem,22rem)] flex-col overflow-hidden rounded-2xl border border-slate-700/90 bg-slate-950/95 shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-slate-700/80 bg-slate-900/90 px-4 py-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Debug</h3>
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          className="rounded-lg px-2 py-1 text-xs font-semibold text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
        >
          Close
        </button>
      </div>
      <div className="max-h-80 space-y-4 overflow-y-auto p-4 text-xs text-slate-300">
        <div>
          <div className="mb-1 font-semibold text-slate-500">WebSocket</div>
          <div className={isConnected ? 'font-medium text-emerald-400' : 'font-medium text-red-400'}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        <div>
          <div className="mb-1 font-semibold text-slate-500">Camera</div>
          <div className="break-all font-mono text-[11px] text-slate-200">{selectedCamera ?? '—'}</div>
        </div>

        <div>
          <div className="mb-1 font-semibold text-slate-500">Swimmers</div>
          <div className="font-mono text-sm font-semibold text-slate-100">{swimmers.length}</div>
        </div>

        {swimmers.length > 0 && (
          <div>
            <div className="mb-2 font-semibold text-slate-500">Sample payload</div>
            <pre className="max-h-40 overflow-auto rounded-lg border border-slate-700/80 bg-slate-900/80 p-2 font-mono text-[10px] leading-relaxed text-slate-300">
              {JSON.stringify(swimmers.slice(0, 2), null, 2)}
              {swimmers.length > 2 && `\n… +${swimmers.length - 2} more`}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
