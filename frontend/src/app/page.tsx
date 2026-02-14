import { getAnalyticsSummary, getTransactions } from "@/lib/api";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { RecentDecisions } from "@/components/dashboard/RecentDecisions";
import { RiskDistribution } from "@/components/dashboard/RiskDistribution";
import type { AnalyticsSummary, TransactionRecord } from "@/lib/types";

export default async function DashboardPage() {
  // Fetch data in parallel
  let analytics: AnalyticsSummary;
  let recentTransactions: TransactionRecord[];
  let error: string | null = null;

  try {
    [analytics, recentTransactions] = await Promise.all([
      getAnalyticsSummary(),
      getTransactions(5, 0)
    ]);
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to fetch dashboard data";
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
    recentTransactions = [];
  }

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Multi-agent fraud detection system overview
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-lg">
          <p className="font-medium">Failed to load dashboard data</p>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-sm mt-1">Make sure the backend is running on http://localhost:8000</p>
        </div>
      )}

      {/* Stats Cards */}
      <StatsCards analytics={analytics} />

      {/* Row: Recent Decisions + Risk Distribution */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RecentDecisions transactions={recentTransactions} />
        </div>
        <div className="lg:col-span-1">
          <RiskDistribution breakdown={analytics.decisions_breakdown} />
        </div>
      </div>
    </div>
  );
}
