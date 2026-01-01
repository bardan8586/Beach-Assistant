/**
 * Data Debug Panel
 * ================
 * Show all incoming data for debugging
 */

import { useState } from 'react'
import type { Swimmer } from '../../types/swimmer'

interface DataDebugPanelProps {
  swimmers: Swimmer[]
  isConnected: boolean
}

export default function DataDebugPanel({ swimmers, isConnected }: DataDebugPanelProps) {
  const [isOpen, setIsOpen] = useState(false)

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg text-sm hover:bg-gray-700 z-50"
      >
        🔍 Debug Data
      </button>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-2xl border-2 border-gray-300 w-96 max-h-96 z-50">
      <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
        <h3 className="font-bold text-gray-900">🔍 Debug Panel</h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>
      <div className="p-4 overflow-y-auto max-h-80">
        <div className="space-y-4 text-xs">
          <div>
            <div className="font-semibold text-gray-700 mb-1">Connection Status:</div>
            <div className={isConnected ? 'text-green-600' : 'text-red-600'}>
              {isConnected ? '✅ WebSocket Connected' : '❌ WebSocket Disconnected'}
            </div>
          </div>
          
          <div>
            <div className="font-semibold text-gray-700 mb-1">Swimmers Count:</div>
            <div className="text-gray-900">{swimmers.length}</div>
          </div>

          {swimmers.length > 0 && (
            <div>
              <div className="font-semibold text-gray-700 mb-2">Swimmer Data:</div>
              <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                {JSON.stringify(swimmers.slice(0, 3), null, 2)}
                {swimmers.length > 3 && '\n... and ' + (swimmers.length - 3) + ' more'}
              </pre>
            </div>
          )}

          {swimmers.length === 0 && (
            <div className="text-yellow-600">
              ⚠️ No swimmer data received yet. Check:
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Is AI pipeline running?</li>
                <li>Is backend receiving data?</li>
                <li>Check browser console for errors</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

