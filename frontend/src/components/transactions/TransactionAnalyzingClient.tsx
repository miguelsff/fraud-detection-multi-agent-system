"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, AlertCircle } from "lucide-react";
import { TransactionDetailCard } from "@/components/transactions/TransactionDetailCard";
import { TransactionDetailClient } from "@/components/transactions/TransactionDetailClient";
import { AgentTraceTimeline } from "@/components/agents/AgentTraceTimeline";
import { WebSocketStatus } from "@/components/common/WebSocketStatus";
import { useWebSocket } from "@/hooks/useWebSocket";
import { getTransactionDetail, getTransactionTrace } from "@/lib/api";
import type {
  Transaction,
  CustomerBehavior,
  TransactionAnalysisDetail,
  AgentTraceEntry,
} from "@/lib/types";

const ALL_AGENTS = [
  "validate_input",
  "transaction_context",
  "behavioral_pattern",
  "policy_rag",
  "external_threat",
  "evidence_aggregation",
  "debate_pro_fraud",
  "debate_pro_customer",
  "decision_arbiter",
  "explainability",
];

interface TransactionAnalyzingClientProps {
  transactionId: string;
}

export function TransactionAnalyzingClient({ transactionId }: TransactionAnalyzingClientProps) {
  const router = useRouter();
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [customerBehavior, setCustomerBehavior] = useState<CustomerBehavior | null>(null);
  const [detail, setDetail] = useState<TransactionAnalysisDetail | null>(null);
  const [trace, setTrace] = useState<AgentTraceEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const hasLoadedResultRef = useRef(false);

  const { events, isConnected, lastEvent } = useWebSocket({
    transactionId,
    autoConnect: true,
  });

  // Read data from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem(`analyzing:${transactionId}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setTransaction(parsed.transaction);
        setCustomerBehavior(parsed.customer_behavior);
      } catch {
        // Ignore parse errors
      }
    }
  }, [transactionId]);

  // Count completed agents from WS events
  const completedAgents = new Set(
    events
      .filter((e) => e.event === "agent_completed" && e.agent)
      .map((e) => e.agent!)
  );
  const completedCount = completedAgents.size;

  // Load full results from API
  const loadResults = useCallback(async () => {
    if (hasLoadedResultRef.current) return;
    try {
      const [detailData, traceData] = await Promise.all([
        getTransactionDetail(transactionId),
        getTransactionTrace(transactionId),
      ]);
      hasLoadedResultRef.current = true;
      setDetail(detailData);
      setTrace(traceData);

      // Clean up sessionStorage
      sessionStorage.removeItem(`analyzing:${transactionId}`);

      // Replace URL to remove ?analyzing=true
      router.replace(`/transactions/${transactionId}`);
    } catch {
      // Not ready yet, will retry
    }
  }, [transactionId, router]);

  // When decision_ready arrives, fetch full results
  useEffect(() => {
    if (lastEvent?.event === "decision_ready") {
      // Small delay to ensure DB persistence completes
      setTimeout(loadResults, 500);
    }
    if (lastEvent?.event === "analysis_error") {
      const errorMsg =
        (lastEvent.data?.error as string) || "Error desconocido durante el análisis";
      setError(errorMsg);
    }
  }, [lastEvent, loadResults]);

  // Polling fallback: if no WS events after 10s, try loading; then every 15s
  useEffect(() => {
    const initialTimeout = setTimeout(() => {
      if (!hasLoadedResultRef.current && events.length === 0) {
        loadResults();
      }
    }, 10000);

    pollingRef.current = setInterval(() => {
      if (!hasLoadedResultRef.current) {
        loadResults();
      }
    }, 15000);

    return () => {
      clearTimeout(initialTimeout);
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [events.length, loadResults]);

  // If we have loaded the full detail+trace, render the complete view
  if (detail && trace) {
    return (
      <TransactionDetailClient
        transactionId={transactionId}
        detail={detail}
        trace={trace}
      />
    );
  }

  // Build placeholder trace entries for the timeline (all agents as idle placeholders)
  const placeholderTrace: AgentTraceEntry[] = ALL_AGENTS.map((name) => ({
    agent_name: name,
    timestamp: new Date().toISOString(),
    duration_ms: 0,
    input_summary: "",
    output_summary: "",
    status: "skipped" as const,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Transacción {transactionId}
          </h1>
          <p className="text-muted-foreground mt-1">
            Análisis en progreso...
          </p>
        </div>
        <WebSocketStatus isConnected={isConnected} />
      </div>

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-destructive">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <div>
                <p className="font-medium">Error en el análisis</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 2-Column Grid (same layout as TransactionDetailClient) */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {transaction && (
            <TransactionDetailCard
              transaction={transaction}
              customerBehavior={customerBehavior}
              transactionSignals={null}
              behavioralSignals={null}
            />
          )}

          <AgentTraceTimeline trace={placeholderTrace} liveEvents={events} />
        </div>

        {/* Right Column - Decision pending */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Decisión</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-8 text-center space-y-4">
                <Loader2 className="h-10 w-10 text-muted-foreground animate-spin" />
                <div>
                  <p className="text-sm font-medium">
                    Analizando transacción...
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {completedCount}/{ALL_AGENTS.length} agentes completados
                  </p>
                </div>
                {/* Progress bar */}
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary rounded-full h-2 transition-all duration-500"
                    style={{ width: `${(completedCount / ALL_AGENTS.length) * 100}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
