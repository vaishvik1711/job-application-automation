import { useWebSocketContext } from '@/services/WebSocketProvider'
import { Badge } from '@/components/ui/Badge'
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react'

interface WebSocketStatusProps {
  compact?: boolean
  showMessages?: boolean
}

export function WebSocketStatus({ compact = false, showMessages = true }: WebSocketStatusProps) {
  const { connectionState, isConnected, lastMessage, messages, connect } = useWebSocketContext()

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <Badge
          variant={isConnected ? 'success' : connectionState === 'connecting' ? 'warning' : 'danger'}
          className="flex items-center gap-1 text-xs"
        >
          {connectionState === 'connected' && <Wifi className="w-3 h-3" />}
          {connectionState === 'connecting' && <RefreshCw className="w-3 h-3 animate-spin" />}
          {connectionState === 'disconnected' && <WifiOff className="w-3 h-3" />}
          {connectionState === 'error' && <AlertCircle className="w-3 h-3" />}
          {isConnected ? 'Live' : connectionState === 'connecting' ? 'Connecting...' : 'Offline'}
        </Badge>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <Badge
          variant={isConnected ? 'success' : connectionState === 'connecting' ? 'warning' : 'danger'}
          className="flex items-center gap-1.5 text-xs"
        >
          {connectionState === 'connected' && <Wifi className="w-3 h-3" />}
          {connectionState === 'connecting' && <RefreshCw className="w-3 h-3 animate-spin" />}
          {connectionState === 'disconnected' && <WifiOff className="w-3 h-3" />}
          {connectionState === 'error' && <AlertCircle className="w-3 h-3" />}
          {connectionState === 'connected'
            ? 'Connected to real-time updates'
            : connectionState === 'connecting'
            ? 'Connecting to server...'
            : 'Disconnected from server'}
        </Badge>

        {!isConnected && (connectionState === 'disconnected' || connectionState === 'error') && (
          <button
            onClick={connect}
            className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 hover:dark:text-primary-300"
          >
            Reconnect
          </button>
        )}
      </div>

      {showMessages && messages.length > 0 && (
        <div className="text-xs text-slate-500 dark:text-slate-400">
          {messages.length} event{messages.length !== 1 ? 's' : ''} received
          {lastMessage && (
            <span className="ml-2 text-slate-400 dark:text-slate-500">
              last: {lastMessage.type}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
