import { io, Socket } from 'socket.io-client'
import type { PipelineProgress } from '@/types'
import { useUIStore, useJobSearchStore } from '@/store'

export type WebSocketEventType =
  | 'pipeline_update'
  | 'job_found'
  | 'match_complete'
  | 'resume_generated'
  | 'error'
  | 'progress'
  | 'connect'
  | 'disconnect'

export type WebSocketListener = (payload: unknown) => void

class WebSocketService {
  private socket: Socket | null = null
  private listeners: Map<WebSocketEventType, Set<WebSocketListener>> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  connect() {
    if (this.socket) {
      return
    }

    // Build the WebSocket URL from VITE_API_URL (the backend) so we
    // connect to the Railway API server, not the Cloudflare Pages frontend origin.
    const apiUrl = (import.meta as any).env?.VITE_API_URL
    let wsUrl: string

    if (apiUrl && apiUrl.startsWith('http')) {
      // Production: convert http(s)://... → ws(s)://...
      const protocol = apiUrl.startsWith('https') ? 'wss' : 'ws'
      wsUrl = apiUrl.replace(/^https?:\/\//, `${protocol}://`)
    } else {
      // Dev / fallback: use the current page origin
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const host = window.location.hostname
      const port = window.location.port
      wsUrl = port ? `${protocol}://${host}:${port}` : `${protocol}://${host}`
    }

    try {
      this.socket = io(wsUrl, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay,
        reconnectionDelayMax: 5000,
        timeout: 10000,
        autoConnect: true,
      })

      this.socket.on('connect', () => {
        this.reconnectAttempts = 0
        this.emit('connect', null)
      })

      this.socket.on('disconnect', (reason: string) => {
        this.emit('disconnect', reason)
      })

      this.socket.on('connect_error', (error: Error) => {
        console.warn('WebSocket connection error:', error.message)
        this.reconnectAttempts++
        this.emit('error', { message: error.message, reconnectAttempt: this.reconnectAttempts })
      })

      // Listen for all message types from backend
      this.socket.on('pipeline_update', (payload: PipelineProgress) => {
        this.emit('pipeline_update', payload)
        this.dispatch('pipeline_update', payload)
      })

      this.socket.on('job_found', (payload: unknown) => {
        this.emit('job_found', payload)
        this.dispatch('job_found', payload)
      })

      this.socket.on('match_complete', (payload: unknown) => {
        this.emit('match_complete', payload)
        this.dispatch('match_complete', payload)
      })

      this.socket.on('resume_generated', (payload: unknown) => {
        this.emit('resume_generated', payload)
        this.dispatch('resume_generated', payload)
      })

      this.socket.on('progress', (payload: PipelineProgress) => {
        this.emit('progress', payload)
        this.dispatch('progress', payload)
      })

      this.socket.on('error', (error: Error) => {
        this.emit('error', error)
      })
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error)
      this.emit('error', { message: 'Failed to initialize WebSocket connection' })
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.listeners.clear()
  }

  subscribe(eventType: WebSocketEventType, listener: WebSocketListener) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType)?.add(listener)

    // Return unsubscribe function
    return () => {
      this.listeners.get(eventType)?.delete(listener)
    }
  }

  emit(eventType: WebSocketEventType, payload: unknown) {
    const listeners = this.listeners.get(eventType)
    if (listeners) {
      listeners.forEach((listener) => {
        try {
          listener(payload)
        } catch (err) {
          console.error('WebSocket listener error:', err)
        }
      })
    }
  }

  // Internal dispatch for state management integration
  private dispatch(eventType: string, payload: unknown) {
    const { addNotification } = useUIStore.getState()
    const { setSearchProgress, setSearching } = useJobSearchStore.getState()

    switch (eventType) {
      case 'pipeline_update': {
        const progress = payload as PipelineProgress
        setSearching(true)
        setSearchProgress({
          current: progress.current,
          total: progress.total,
          message: progress.message,
        })

        if (progress.current >= progress.total) {
          setSearching(false)
          setSearchProgress(null)
          addNotification({
            type: 'success',
            message: `Pipeline stage "${progress.stage}" completed`,
          })
        } else {
          addNotification({
            type: 'info',
            message: `Pipeline: ${progress.message}`,
          })
        }
        break
      }

      case 'job_found': {
        addNotification({
          type: 'info',
          message: 'New job discovered!',
        })
        break
      }

      case 'match_complete': {
        addNotification({
          type: 'success',
          message: 'Job matching analysis complete',
        })
        break
      }

      case 'resume_generated': {
        addNotification({
          type: 'success',
          message: 'Resume generated successfully',
        })
        break
      }

      case 'error': {
        const error = payload as { message: string }
        addNotification({
          type: 'error',
          message: error.message || 'WebSocket error',
        })
        break
      }

      case 'progress': {
        const progress = payload as PipelineProgress
        setSearchProgress({
          current: progress.current,
          total: progress.total,
          message: progress.message,
        })
        break
      }

      case 'connect':
        addNotification({
          type: 'success',
          message: 'Connected to real-time updates',
        })
        break

      case 'disconnect':
        addNotification({
          type: 'warning',
          message: 'Disconnected from server. Reconnecting...',
        })
        break
    }
  }

  getConnectionState(): 'connecting' | 'connected' | 'disconnected' | 'error' {
    if (!this.socket) return 'disconnected'
    if (this.socket.connected) return 'connected'
    if (this.reconnectAttempts > 0) return 'connecting'
    return 'disconnected'
  }

  sendMessage(eventType: WebSocketEventType, payload: unknown) {
    if (this.socket && this.socket.connected) {
      this.socket.emit(eventType, payload)
    } else {
      console.warn('WebSocket: Cannot send message, not connected')
    }
  }
}

export const websocketService = new WebSocketService()

export default WebSocketService
