"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WebSocketEvent } from "@/lib/types";

interface UseWebSocketOptions {
  transactionId?: string;
  autoConnect?: boolean;
  maxReconnectDelay?: number;
}

interface UseWebSocketReturn {
  events: WebSocketEvent[];
  isConnected: boolean;
  lastEvent: WebSocketEvent | null;
  connect: () => void;
  disconnect: () => void;
}

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { transactionId, autoConnect = true, maxReconnectDelay = 30000 } = options;

  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelayRef = useRef(1000); // Start with 1s
  const shouldConnectRef = useRef(autoConnect);

  const connect = useCallback(() => {
    // Don't connect if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      const url = transactionId
        ? `${WS_BASE_URL}/api/v1/ws/transactions?transaction_id=${transactionId}`
        : `${WS_BASE_URL}/api/v1/ws/transactions`;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WebSocket] Connected");
        setIsConnected(true);
        reconnectDelayRef.current = 1000; // Reset delay on successful connection
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          setEvents((prev) => [...prev, data]);
          setLastEvent(data);
        } catch (error) {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
      };

      ws.onclose = (event) => {
        console.log("[WebSocket] Disconnected", event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconnect with exponential backoff if connection was intended
        if (shouldConnectRef.current) {
          const delay = Math.min(reconnectDelayRef.current, maxReconnectDelay);
          console.log(`[WebSocket] Reconnecting in ${delay}ms...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, maxReconnectDelay);
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error("[WebSocket] Connection failed:", error);
      setIsConnected(false);
    }
  }, [transactionId, maxReconnectDelay]);

  const disconnect = useCallback(() => {
    shouldConnectRef.current = false;

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      shouldConnectRef.current = true;
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    events,
    isConnected,
    lastEvent,
    connect,
    disconnect,
  };
}
