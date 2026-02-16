"use client";

import { TransactionDetailCard } from "@/components/transactions/TransactionDetailCard";
import { DecisionCard } from "@/components/transactions/DecisionCard";
import { AgentTraceTimeline } from "@/components/agents/AgentTraceTimeline";
import { DebateView } from "@/components/agents/DebateView";
import { CustomerExplanation } from "@/components/explanation/CustomerExplanation";
import { AuditExplanation } from "@/components/explanation/AuditExplanation";
import { WebSocketStatus } from "@/components/common/WebSocketStatus";
import { useWebSocket } from "@/hooks/useWebSocket";
import type {
  TransactionAnalysisDetail,
  AgentTraceEntry,
} from "@/lib/types";

interface TransactionDetailClientProps {
  transactionId: string;
  detail: TransactionAnalysisDetail;
  trace: AgentTraceEntry[];
}

export function TransactionDetailClient({
  transactionId,
  detail,
  trace,
}: TransactionDetailClientProps) {
  // Connect to WebSocket for live updates
  const { events, isConnected } = useWebSocket({
    transactionId,
    autoConnect: true,
  });

  return (
    <div className="space-y-6">
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Transacción {transactionId}
          </h1>
          <p className="text-muted-foreground mt-1">
            Análisis completo de fraude y traza de ejecución de agentes
          </p>
        </div>
        <WebSocketStatus isConnected={isConnected} />
      </div>

      {/* 2-Column Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          <TransactionDetailCard
            transaction={detail.transaction}
            customerBehavior={detail.customer_behavior}
            transactionSignals={detail.transaction_signals}
            behavioralSignals={detail.behavioral_signals}
          />

          {/* Pass live events to timeline */}
          <AgentTraceTimeline trace={trace} liveEvents={events} />

          {detail.debate && (
            <DebateView
              debate={detail.debate}
              decision={{
                decision: detail.decision,
                confidence: detail.confidence,
                reasoning: detail.explanation?.audit_explanation || "",
              }}
            />
          )}
        </div>

        {/* Right Column (1/3 width) */}
        <div className="lg:col-span-1 space-y-6">
          <DecisionCard
            decision={detail.decision}
            confidence={detail.confidence}
            evidence={detail.evidence}
            signals={detail.transaction_signals}
          />

          {detail.explanation && (
            <>
              <CustomerExplanation
                explanation={detail.explanation.customer_explanation}
                decision={{
                  decision: detail.decision,
                  confidence: detail.confidence,
                  reasoning: detail.explanation.audit_explanation,
                }}
              />
              <AuditExplanation
                explanation={detail.explanation.audit_explanation}
                decision={{
                  decision: detail.decision,
                  confidence: detail.confidence,
                  reasoning: detail.explanation.audit_explanation,
                }}
                policyMatches={detail.policy_matches}
                evidence={detail.evidence}
                trace={trace}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
