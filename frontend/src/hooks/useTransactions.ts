"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { getTransactions } from "@/lib/api";
import type { TransactionRecord } from "@/lib/types";

interface UseTransactionsOptions {
  limit?: number;
  offset?: number;
  refreshInterval?: number; // in seconds, 0 = no polling
}

interface UseTransactionsReturn {
  transactions: TransactionRecord[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTransactions(options: UseTransactionsOptions = {}): UseTransactionsReturn {
  const { limit = 100, offset = 0, refreshInterval = 30 } = options;

  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchTransactions = useCallback(async () => {
    try {
      setError(null);
      const data = await getTransactions(limit, offset);
      setTransactions(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to fetch transactions";
      setError(errorMessage);
      console.error("[useTransactions] Error:", errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [limit, offset]);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    await fetchTransactions();
  }, [fetchTransactions]);

  // Initial fetch
  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  // Polling
  useEffect(() => {
    if (refreshInterval > 0) {
      intervalRef.current = setInterval(() => {
        fetchTransactions();
      }, refreshInterval * 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [refreshInterval, fetchTransactions]);

  return {
    transactions,
    isLoading,
    error,
    refresh,
  };
}
