import { createContext, useContext, ReactNode, useState, useRef, useCallback, useEffect } from 'react'
import { websocketService, WebSocketEventType, WebSocketListener } from '@/services/websocket'
import type { WSMessage, PipelineProgress } from '@/types'
import { useUIStore } from '@/store'
import { toast } from 'sonner'

interface WebSocketContextType {
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error'
  isConnected: boolean
  lastMessage: WSMessage | null
  messages: WSMessage[]
  sendMessage: (type: WebSocketEventType, payload: unknown) => void
  subscribe: (eventType: WebSocketEventType, listener: WebSocketListener) => () => void
  connect: () => void
  disconnect: () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: ReactNode
  autoConnect?: boolean
}

export function WebSocketProvider({ children, autoConnect = true }: WebSocketProviderProps) {
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)
  const [messages, setMessages] = useState<WSMessage[]>([])
  const { addNotification } = useUIStore()
  const connectTimeoutRef = useRef<number | null>(null)
  const unsubscribeRefs = useRef<(() => void)[]>([])

  const clearConnectTimeout = () => {
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current)
      connectTimeoutRef.current = null
    }
  }

  const connect = useCallback(() => {
    websocketService.connect()
    setConnectionState('connecting')

    // Fallback: if we're still "connecting" after 15 s, assume the server is
    // unreachable and drop to "disconnected" so the Reconnect button appears.
    clearConnectTimeout()
    connectTimeoutRef.current = window.setTimeout(() => {
      if (websocketService.getConnectionState() !== 'connected') {
        setConnectionState('disconnected')
      }
    }, 15000)
  }, [])

  const disconnect = useCallback(() => {
    clearConnectTimeout()
    // Clean up existing subscriptions
    unsubscribeRefs.current.forEach((unsub) => unsub())
    unsubscribeRefs.current = []
    websocketService.disconnect()
    setConnectionState('disconnected')
  }, [])

  const sendMessage = useCallback((type: WebSocketEventType, payload: unknown) => {
    websocketService.sendMessage(type, payload)
  }, [])

  const subscribe = useCallback((eventType: WebSocketEventType, listener: WebSocketListener) => {
    return websocketService.subscribe(eventType, listener)
  }, [])

  // Event handlers
  const handlePipelineUpdate = (payload: unknown) => {
    const progress = payload as PipelineProgress
    setLastMessage({
      type: 'pipeline_update',
      payload,
      timestamp: new Date().toISOString(),
    })
    setMessages((prev) => [...prev.slice(-49), {
      type: 'pipeline_update',
      payload,
      timestamp: new Date().toISOString(),
    }])
    clearConnectTimeout()

    if (progress.current >= progress.total) {
      setConnectionState('connected')
      addNotification({
        type: 'success',
        message: `Pipeline stage "${progress.stage}" completed`,
      })
      toast.success(`Pipeline: ${progress.message}`)
    } else {
      addNotification({
        type: 'info',
        message: `Pipeline: ${progress.message}`,
      })
    }
  }

  const handleJobFound = () => {
    addNotification({ type: 'info', message: 'New job discovered!' })
    toast.info('New job found matching your criteria')
  }

  const handleMatchComplete = () => {
    addNotification({ type: 'success', message: 'Job matching analysis complete' })
    toast.success('Match analysis complete')
  }

  const handleResumeGenerated = () => {
    addNotification({ type: 'success', message: 'Resume generated successfully' })
    toast.success('Resume generated!')
  }

  const handleError = (payload: unknown) => {
    const error = payload as { message: string }
    addNotification({ type: 'error', message: error?.message || 'WebSocket error' })
    toast.error(error?.message || 'Connection error')
    // Transition to disconnected so the Reconnect button is available.
    setConnectionState('disconnected')
  }

  const handleProgress = (payload: unknown) => {
    const progress = payload as PipelineProgress
    addNotification({ type: 'info', message: progress.message })
  }

  // Auto-connect and set up global listeners on mount.
  useEffect(() => {
    if (!autoConnect) return

    connect()

    const unsubList = [
      websocketService.subscribe('connect', () => {
        clearConnectTimeout()
        setConnectionState('connected')
      }),
      websocketService.subscribe('disconnect', () => setConnectionState('disconnected')),
      websocketService.subscribe('pipeline_update', handlePipelineUpdate),
      websocketService.subscribe('job_found', handleJobFound),
      websocketService.subscribe('match_complete', handleMatchComplete),
      websocketService.subscribe('resume_generated', handleResumeGenerated),
      websocketService.subscribe('error', handleError),
      websocketService.subscribe('progress', handleProgress),
    ]
    unsubscribeRefs.current = unsubList

    return () => {
      clearConnectTimeout()
      unsubList.forEach((unsub) => unsub())
      websocketService.disconnect()
    }
  }, [autoConnect, connect])

  return (
    <WebSocketContext.Provider
      value={{
        connectionState,
        isConnected: connectionState === 'connected',
        lastMessage,
        messages,
        sendMessage,
        subscribe,
        connect,
        disconnect,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}
