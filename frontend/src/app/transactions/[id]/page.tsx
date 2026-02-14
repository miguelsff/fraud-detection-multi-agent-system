import { notFound } from "next/navigation";
import { getTransactionDetail, getTransactionTrace } from "@/lib/api";
import { TransactionDetailCard } from "@/components/transactions/TransactionDetailCard";
import { DecisionCard } from "@/components/transactions/DecisionCard";
import { AgentTraceTimeline } from "@/components/agents/AgentTraceTimeline";
import { DebateView } from "@/components/agents/DebateView";
import { CustomerExplanation } from "@/components/explanation/CustomerExplanation";
import { AuditExplanation } from "@/components/explanation/AuditExplanation";

interface TransactionDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function TransactionDetailPage({
  params
}: TransactionDetailPageProps) {
  const { id: transactionId } = await params;

  let detail, trace;
  let error: string | null = null;

  try {
    // Parallel data fetching
    [detail, trace] = await Promise.all([
      getTransactionDetail(transactionId),
      getTransactionTrace(transactionId),
    ]);
  } catch (err: any) {
    if (err?.status === 404) {
      notFound();
    }
    error = err?.message || "Failed to load transaction";
  }

  if (error || !detail || !trace) {
    return (
      <div className="space-y-4">
        <h1 className="text-3xl font-bold">Error Loading Transaction</h1>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Transaction {transactionId}
        </h1>
        <p className="text-muted-foreground mt-1">
          Complete fraud analysis and agent execution trace
        </p>
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

          <AgentTraceTimeline trace={trace} />

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
