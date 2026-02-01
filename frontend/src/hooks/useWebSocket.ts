/**
 * WebSocket Hook
 * ==============
 * Custom React hook for WebSocket connection
 */

import { useEffect, useRef, useState } from 'react'
import { WS_URL, WS_RECONNECT_INTERVAL } from '../utils/constants'
import type { FrameResult, SwimmerData, AlertData } from '../types/frameResult'

/** Backend may send full FrameResult (swimmers, alerts) or legacy { type, data, camera_id } */
export interface WebSocketMessage {
  type?: 'swimmers' | 'alert' | 'heatmap' | 'frame_result'
  data?: unknown
  frame_result?: FrameResult
  timestamp?: number | string
  camera_id?: string
  /** Present when backend sends FrameResult as message body */
  swimmers?: SwimmerData[]
  alerts?: AlertData[]
}

interface UseWebSocketOptions {
  cameraId: string
  onMessage?: (message: WebSocketMessage) => void
  autoConnect?: boolean
}

export function useWebSocket({
  cameraId,
  onMessage,
  autoConnect = true,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | undefined>(undefined)

  const connect = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return // Already connected
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    try {
      const wsUrl = `${WS_URL}/ws/feed?camera_id=${cameraId || 'all'}`
      console.log(`🔌 Connecting to WebSocket: ${wsUrl}`)
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('✅ WebSocket connected successfully')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          console.log('📨 WebSocket message received:', message.type)
          setLastMessage(message)
          if (onMessage) {
            onMessage(message)
          }
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error, event.data)
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket error event:', error)
        console.error('   URL:', wsUrl)
        console.error('   ReadyState:', ws.readyState)
        setIsConnected(false)
      }

      ws.onclose = (event) => {
        console.log(`🔌 WebSocket disconnected (code: ${event.code}, reason: ${event.reason || 'none'})`)
        setIsConnected(false)
        
        // Only auto-reconnect if not a normal closure
        if (event.code !== 1000) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log('🔄 Attempting to reconnect...')
            connect()
          }, WS_RECONNECT_INTERVAL)
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('❌ Failed to create WebSocket:', error)
      setIsConnected(false)
    }
  }

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = undefined
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
    setIsConnected(false)
  }

  useEffect(() => {
    if (autoConnect && cameraId) {
      // Small delay to ensure previous connection is closed
      const timeoutId = setTimeout(() => {
        connect()
      }, 100)
      
      return () => {
        clearTimeout(timeoutId)
        disconnect()
      }
    }
    
    return () => {
      disconnect()
    }
  }, [cameraId, autoConnect])

  return {
    isConnected,
    lastMessage,
    connect,
    disconnect,
  }
}

