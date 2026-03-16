import { useEffect, useRef, useCallback } from "react"
import { useAppStore } from "../stores/appStore"

const WS_URL = `ws://${window.location.hostname}:8000/ws`
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 10000]

export function useWebSocket() {
  const wsRef = useRef(null)
  const reconnectAttempt = useRef(0)
  const reconnectTimer = useRef(null)
  const { setConnected, handleEvent } = useAppStore()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      console.log("[WS] connected to", WS_URL)
      setConnected(true)
      reconnectAttempt.current = 0
    }

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        console.log("[WS] received:", event.type, event.data)
        handleEvent(event)
      } catch {
        // ignore non-JSON messages
      }
    }

    ws.onclose = () => {
      console.log("[WS] disconnected, reconnecting...")
      setConnected(false)
      const delay =
        RECONNECT_DELAYS[
          Math.min(reconnectAttempt.current, RECONNECT_DELAYS.length - 1)
        ]
      reconnectAttempt.current++
      reconnectTimer.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [setConnected, handleEvent])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { sendMessage }
}
