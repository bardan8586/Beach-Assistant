/**
 * WebSocket Hook
 * ==============
 * Custom React hook for WebSocket connection
 */

import { useEffect, useRef, useState } from 'react'
import { WS_URL, WS_RECONNECT_INTERVAL } from '../utils/constants'

interface WebSocketMessage {
  type: 'swimmers' | 'alert' | 'heatmap'
  data: any
  timestamp: string
  camera_id: string
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
      return // Already connected
    }

    try {
      const wsUrl = `${WS_URL}/ws/feed?camera_id=${cameraId}`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('✅ WebSocket connected')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          onMessage?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('🔌 WebSocket disconnected')
        setIsConnected(false)
        
        // Auto-reconnect
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('🔄 Attempting to reconnect...')
          connect()
        }, WS_RECONNECT_INTERVAL)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    wsRef.current?.close()
    wsRef.current = null
    setIsConnected(false)
  }

  useEffect(() => {
    if (autoConnect) {
      connect()
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

