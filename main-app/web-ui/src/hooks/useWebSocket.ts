import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useStore } from '../store'

interface ProgressUpdate {
  type: string
  job_id: string
  status: string
  step?: string
  progress?: number
  message?: string
  error?: string
}

// Statuses that indicate a major state change worth refetching job data for
const REFETCH_STATUSES = ['script_ready', 'completed', 'failed', 'processing', 'approved']

export const useWebSocket = (jobId: string | null) => {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 10
  const { updateJobProgress, setJobStatus } = useStore()
  const queryClient = useQueryClient()

  const connect = useCallback(() => {
    if (!jobId) return

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${jobId}`
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected for job:', jobId)
      reconnectAttemptsRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const data: ProgressUpdate = JSON.parse(event.data)
        
        if (data.type === 'progress') {
          // Update zustand store with real-time progress
          setJobStatus(jobId, data.status)
          
          if (data.step && data.progress !== undefined) {
            updateJobProgress(jobId, data.step, data.progress, data.message)
          }

          // On major status changes, invalidate react-query cache
          // This triggers a single refetch instead of constant polling
          if (REFETCH_STATUSES.includes(data.status)) {
            queryClient.invalidateQueries({ queryKey: ['job', jobId] })
            queryClient.invalidateQueries({ queryKey: ['jobs'] })
          }
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = (event) => {
      console.log('WebSocket disconnected, code:', event.code)
      wsRef.current = null
      
      // Auto-reconnect with exponential backoff (only for active jobs)
      if (jobId && reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
        reconnectAttemptsRef.current += 1
        console.log(`WebSocket reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`)
        
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, delay)
      }
    }
  }, [jobId, updateJobProgress, setJobStatus, queryClient])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    reconnectAttemptsRef.current = 0
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return { disconnect }
}
