/**
 * WebSocket Hook
 * ==============
 * Connects to the live feed and reconnects with exponential backoff.
 */

import { useEffect, useRef, useState } from 'react'
import { WS_URL, WS_RECONNECT_BASE_MS, WS_RECONNECT_MAX_MS } from '../utils/constants'
import type { FrameResult, SwimmerData, AlertData } from '../types/frameResult'

/** Backend may send full FrameResult (swimmers, alerts) or legacy { type, data, camera_id } */
export interface WebSocketMessage {
  type?: 'swimmers' | 'alert' | 'heatmap' | 'frame_result' | 'connected'
  data?: unknown
  frame_result?: FrameResult
  timestamp?: number | string
  camera_id?: string
  /** Present when backend sends FrameResult as message body */
  swimmers?: SwimmerData[]
  alerts?: AlertData[]
}

export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'offline'

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
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle')
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | undefined>(undefined)
  const heartbeatRef = useRef<number | undefined>(undefined)
  const attemptRef = useRef(0)
  const generationRef = useRef(0)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const clearTimers = () => {
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = undefined
    }
    if (heartbeatRef.current) {
      window.clearInterval(heartbeatRef.current)
      heartbeatRef.current = undefined
    }
  }

  const connect = () => {
    const generation = ++generationRef.current
    clearTimers()

    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }

    setConnectionState(attemptRef.current > 0 ? 'reconnecting' : 'connecting')

    try {
      const wsUrl = `${WS_URL}/ws/feed?camera_id=${encodeURIComponent(cameraId || 'all')}`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        if (generation !== generationRef.current) return
        attemptRef.current = 0
        setConnectionState('connected')
        heartbeatRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 25000)
      }

      ws.onmessage = (event) => {
        if (generation !== generationRef.current) return
        if (event.data === 'pong') return
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          onMessageRef.current?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = () => {
        if (generation !== generationRef.current) return
        setConnectionState('reconnecting')
      }

      ws.onclose = (event) => {
        if (generation !== generationRef.current) return
        setConnectionState('offline')
        if (heartbeatRef.current) {
          window.clearInterval(heartbeatRef.current)
          heartbeatRef.current = undefined
        }
        if (event.code === 1000) return
        const delay = Math.min(
          WS_RECONNECT_MAX_MS,
          WS_RECONNECT_BASE_MS * 2 ** attemptRef.current,
        )
        attemptRef.current += 1
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect()
        }, delay)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      setConnectionState('offline')
    }
  }

  const disconnect = () => {
    generationRef.current += 1
    attemptRef.current = 0
    clearTimers()
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
    setConnectionState('offline')
  }

  useEffect(() => {
    if (!autoConnect || !cameraId) {
      return
    }
    const timeoutId = window.setTimeout(() => {
      connect()
    }, 100)
    return () => {
      window.clearTimeout(timeoutId)
      disconnect()
    }
    // connect/disconnect close over refs; cameraId is the subscription key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraId, autoConnect])

  return {
    isConnected: connectionState === 'connected',
    connectionState,
    lastMessage,
    connect,
    disconnect,
  }
}
