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
  const connectionAttemptsRef = useRef(0);
  const maxConnectionAttempts = 10; // More attempts during active analysis
  const transactionIdRef = useRef(transactionId);

  // Reset events when transactionId changes
  useEffect(() => {
    if (transactionIdRef.current !== transactionId) {
      transactionIdRef.current = transactionId;
      setEvents([]);
      setLastEvent(null);
    }
  }, [transactionId]);

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
        connectionAttemptsRef.current = 0; // Reset connection attempts
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;

          // Client-side filtering: ignore events for other transactions
          if (transactionIdRef.current && data.transaction_id && data.transaction_id !== transactionIdRef.current) {
            return;
          }

          setEvents((prev) => [...prev, data]);
          setLastEvent(data);
        } catch (error) {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      };

      ws.onerror = () => {
        // Don't log WebSocket errors - they're usually connection failures
        // which are expected when backend is not running.
        // The onclose handler will provide better context.
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // Only log if it's not a connection failure (1006 = abnormal closure)
        if (event.code !== 1006) {
          console.log("[WebSocket] Disconnected", event.code, event.reason);
        } else {
          connectionAttemptsRef.current += 1;
        }

        // Auto-reconnect with exponential backoff if connection was intended
        if (shouldConnectRef.current) {
          // Stop trying after max attempts to avoid console spam
          if (connectionAttemptsRef.current >= maxConnectionAttempts) {
            if (process.env.NODE_ENV === "development") {
              console.warn(
                "[WebSocket] Backend not available. Connection attempts exhausted."
              );
            }
            shouldConnectRef.current = false;
            return;
          }

          const delay = Math.min(reconnectDelayRef.current, maxReconnectDelay);

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
    connectionAttemptsRef.current = 0; // Reset attempts on manual disconnect
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
