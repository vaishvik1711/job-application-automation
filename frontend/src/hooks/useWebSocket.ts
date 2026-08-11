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
  // Track if we've already connected
  const connectedRef = useRef(false)

  useEffect(() => {
    if (!autoConnect) return

    websocketService.connect()
    connectedRef.current = true
    setConnectionState('connecting')

    // Subscribe to all message types
    const handleMessage = (payload: unknown) => {
      // Try to parse as WSMessage
      const wsMessage = payload as Partial<WSMessage>
      const message: WSMessage = {
        type: (wsMessage.type as WSMessage['type']) || 'progress',
        payload: wsMessage.payload || payload,
        timestamp: wsMessage.timestamp || new Date().toISOString(),
      }

      setLastMessage(message)
      setMessages((prev) => [...prev.slice(-49), message]) // Keep last 50 messages
    }

    const unsubscribePipeline = websocketService.subscribe('pipeline_update', handleMessage)
    const unsubscribeJobFound = websocketService.subscribe('job_found', handleMessage)
    const unsubscribeMatchComplete = websocketService.subscribe('match_complete', handleMessage)
    const unsubscribeResumeGenerated = websocketService.subscribe('resume_generated', handleMessage)
    const unsubscribeProgress = websocketService.subscribe('progress', handleMessage)
    const unsubscribeError = websocketService.subscribe('error', handleMessage)
    const unsubscribeConnect = () => websocketService.subscribe('connect', () => {
      setConnectionState('connected')
    })
    const unsubscribeDisconnect = () => websocketService.subscribe('disconnect', () => {
      setConnectionState('disconnected')
    })

    // Cleanup
    return () => {
      unsubscribePipeline()
      unsubscribeJobFound()
      unsubscribeMatchComplete()
      unsubscribeResumeGenerated()
      unsubscribeProgress()
      unsubscribeError()
      unsubscribeConnect()
      unsubscribeDisconnect()

      if (connectedRef.current) {
        websocketService.disconnect()
        connectedRef.current = false
      }
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
    connectedRef.current = true
    setConnectionState('connecting')
  }, [])

  const disconnect = useCallback(() => {
    websocketService.disconnect()
    connectedRef.current = false
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
