import { getAnalyticsSummary, getTransactions, getTransactionTrace } from "@/lib/api";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { DecisionBreakdownChart } from "@/components/analytics/DecisionBreakdownChart";
import { ConfidenceDistribution } from "@/components/analytics/ConfidenceDistribution";
import { RiskByCountry } from "@/components/analytics/RiskByCountry";
import { ProcessingTimeChart } from "@/components/analytics/ProcessingTimeChart";
import type { AnalyticsSummary, TransactionRecord } from "@/lib/types";

interface ProcessingTimeData {
  index: number;
  transactionId: string;
  processingTime: number;
  timestamp: string;
}

export default async function AnalyticsPage() {
  // Fetch data in parallel
  let analytics: AnalyticsSummary;
  let transactions: TransactionRecord[];
  let processingTimeData: ProcessingTimeData[] = [];
  let error: string | null = null;

  try {
    // Fetch analytics summary and 200 recent transactions
    [analytics, transactions] = await Promise.all([
      getAnalyticsSummary(),
      getTransactions(200, 0)
    ]);

    // Fetch traces for the 50 most recent transactions to calculate processing times
    const recentTransactions = transactions.slice(0, 50);
    const tracesPromises = recentTransactions.map(t =>
      getTransactionTrace(t.transaction_id).catch(() => [])
    );
    const traces = await Promise.all(tracesPromises);

    // Calculate total processing time per transaction
    processingTimeData = recentTransactions.map((t, idx) => ({
      index: idx + 1,
      transactionId: t.transaction_id,
      processingTime: traces[idx].reduce((sum, trace) => sum + trace.duration_ms, 0),
      timestamp: t.analyzed_at
    }));
  } catch (err) {
    error = err instanceof Error ? err.message : "Error al obtener datos de analítica";
    // Fallback data for error state
    analytics = {
      total_analyzed: 0,
      decisions_breakdown: {
        APPROVE: 0,
        CHALLENGE: 0,
        BLOCK: 0,
        ESCALATE_TO_HUMAN: 0
      },
      avg_confidence: 0,
      escalation_rate: 0,
      avg_processing_time_ms: 0
    };
    transactions = [];
    processingTimeData = [];
  }

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analítica</h1>
        <p className="text-muted-foreground mt-1">
          Información detallada del rendimiento de detección de fraude
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-lg">
          <p className="font-medium">Error al cargar datos de analítica</p>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-sm mt-1">Verifica tu conexión de red o intenta de nuevo más tarde.</p>
        </div>
      )}

      {/* 1. Stats row (reuse from dashboard) */}
      <StatsCards analytics={analytics} />

      {/* 2. Decision breakdown (full width) */}
      <DecisionBreakdownChart breakdown={analytics.decisions_breakdown} />

      {/* 3. Two-column grid: Confidence Distribution + Risk by Country */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ConfidenceDistribution transactions={transactions} />
        <RiskByCountry transactions={transactions} />
      </div>

      {/* 4. Processing time (full width) */}
      <ProcessingTimeChart data={processingTimeData} avgTime={analytics.avg_processing_time_ms} />
    </div>
  );
}
