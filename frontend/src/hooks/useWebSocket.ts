import { useEffect, useState, useCallback, useRef } from 'react'
import { websocketService, WebSocketEventType, WebSocketListener } from '@/services/websocket'
import type { WSMessage, PipelineProgress } from '@/types'

export interface WebSocketState {
  isConnected: boolean
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error'
  lastMessage: WSMessage | null
  messages: WSMessage[]
}

export function useWebSocket(
  autoConnect = true
): WebSocketState & {
  sendMessage: (type: WebSocketEventType, payload: unknown) => void
  subscribe: (eventType: WebSocketEventType, listener: WebSocketListener) => () => void
  connect: () => void
  disconnect: () => void
  clearMessages: () => void
} {
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)
  const [messages, setMessages] = useState<WSMessage[]>([])
  const connectTimeoutRef = useRef<number | null>(null)

  const clearConnectTimeout = () => {
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current)
      connectTimeoutRef.current = null
    }
  }

  useEffect(() => {
    if (!autoConnect) return

    websocketService.connect()
    setConnectionState('connecting')

    // Fallback: if still connecting after 15 s, drop to "disconnected"
    // so the Reconnect button is available.
    connectTimeoutRef.current = window.setTimeout(() => {
      if (websocketService.getConnectionState() !== 'connected') {
        setConnectionState('disconnected')
      }
    }, 15000)

    // Subscribe to all message types
    const handleMessage = (payload: unknown) => {
      const wsMessage = payload as Partial<WSMessage>
      const message: WSMessage = {
        type: (wsMessage.type as WSMessage['type']) || 'progress',
        payload: wsMessage.payload || payload,
        timestamp: wsMessage.timestamp || new Date().toISOString(),
      }

      setLastMessage(message)
      setMessages((prev) => [...prev.slice(-49), message])
    }

    const unsubList = [
      websocketService.subscribe('connect', () => {
        clearConnectTimeout()
        setConnectionState('connected')
      }),
      websocketService.subscribe('disconnect', () => setConnectionState('disconnected')),
      websocketService.subscribe('pipeline_update', handleMessage),
      websocketService.subscribe('job_found', handleMessage),
      websocketService.subscribe('match_complete', handleMessage),
      websocketService.subscribe('resume_generated', handleMessage),
      websocketService.subscribe('progress', handleMessage),
      websocketService.subscribe('error', handleMessage),
    ]

    // Cleanup
    return () => {
      clearConnectTimeout()
      unsubList.forEach((unsub) => unsub())
      websocketService.disconnect()
    }
  }, [autoConnect])

  const sendMessage = useCallback((type: WebSocketEventType, payload: unknown) => {
    websocketService.sendMessage(type, payload)
  }, [])

  const subscribe = useCallback((eventType: WebSocketEventType, listener: WebSocketListener) => {
    return websocketService.subscribe(eventType, listener)
  }, [])

  const connect = useCallback(() => {
    websocketService.connect()
    setConnectionState('connecting')
  }, [])

  const disconnect = useCallback(() => {
    clearConnectTimeout()
    websocketService.disconnect()
    setConnectionState('disconnected')
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setLastMessage(null)
  }, [])

  const isConnected = connectionState === 'connected'

  return {
    isConnected,
    connectionState,
    lastMessage,
    messages,
    sendMessage,
    subscribe,
    connect,
    disconnect,
    clearMessages,
  }
}

// Convenience hook for pipeline progress tracking
export function usePipelineProgress() {
  const [progress, setProgress] = useState<PipelineProgress | null>(null)
  const { subscribe, connectionState, isConnected } = useWebSocket()

  useEffect(() => {
    if (!subscribe) return

    const unsubscribePipeline = subscribe('pipeline_update', (payload) => {
      setProgress(payload as PipelineProgress)
    })

    const unsubscribeProgress = subscribe('progress', (payload) => {
      setProgress(payload as PipelineProgress)
    })

    return () => {
      unsubscribePipeline()
      unsubscribeProgress()
    }
  }, [subscribe])

  const clearProgress = () => setProgress(null)

  return { progress, connectionState, isConnected, clearProgress }
}
