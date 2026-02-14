"use client";

import { useState, useEffect } from "react";
import { healthCheck } from "@/lib/api";

interface SystemHealth {
  isOnline: boolean;
  isChecking: boolean;
}

/**
 * Custom hook to poll system health status.
 * Checks the backend /api/v1/health endpoint at regular intervals.
 *
 * @param intervalMs - Polling interval in milliseconds (default: 30000 = 30 seconds)
 * @returns SystemHealth object with isOnline and isChecking status
 */
export function useSystemHealth(intervalMs: number = 30000): SystemHealth {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      if (!isMounted) return;

      setIsChecking(true);
      try {
        await healthCheck();
        if (isMounted) {
          setIsOnline(true);
        }
      } catch (error) {
        if (isMounted) {
          setIsOnline(false);
        }
      } finally {
        if (isMounted) {
          setIsChecking(false);
        }
      }
    };

    // Check immediately on mount
    checkHealth();

    // Set up polling interval
    const intervalId = setInterval(checkHealth, intervalMs);

    // Cleanup on unmount
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [intervalMs]);

  return { isOnline, isChecking };
}
