/**
 * TypeScript interfaces mirroring Pydantic models from backend.
 * Source: backend/app/models/
 */

// ============================================================================
// Transaction Models (backend/app/models/transaction.py)
// ============================================================================

export interface Transaction {
  transaction_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  country: string;
  channel: string;
  device_id: string;
  timestamp: string; // ISO 8601 datetime string
  merchant_id: string;
}

export interface CustomerBehavior {
  customer_id: string;
  usual_amount_avg: number;
  usual_hours: string;
  usual_countries: string[];
  usual_devices: string[];
}

// ============================================================================
// Signal Models (backend/app/models/signals.py)
// ============================================================================

export type ChannelRisk = "low" | "medium" | "high";

export interface TransactionSignals {
  amount_ratio: number;
  is_off_hours: boolean;
  is_foreign: boolean;
  is_unknown_device: boolean;
  channel_risk: ChannelRisk;
  flags: string[];
}

export interface BehavioralSignals {
  deviation_score: number; // 0.0 - 1.0
  anomalies: string[];
  velocity_alert: boolean;
}

// ============================================================================
// Evidence Models (backend/app/models/evidence.py)
// ============================================================================

export type RiskCategory = "low" | "medium" | "high" | "critical";

export interface PolicyMatch {
  policy_id: string;
  description: string; // Note: backend uses 'description', not 'matched_text'
  relevance_score: number; // 0.0 - 1.0
}

export interface PolicyMatchResult {
  matches: PolicyMatch[];
  chunk_ids: string[];
}

export interface ThreatSource {
  source_name: string;
  confidence: number; // 0.0 - 1.0
}

export interface ThreatIntelResult {
  threat_level: number; // 0.0 - 1.0
  sources: ThreatSource[];
}

export interface AggregatedEvidence {
  composite_risk_score: number; // 0.0 - 100.0
  all_signals: string[];
  all_citations: string[];
  risk_category: RiskCategory;
}

// ============================================================================
// Debate Models (backend/app/models/debate.py)
// ============================================================================

export interface DebateArguments {
  pro_fraud_argument: string;
  pro_fraud_confidence: number; // 0.0 - 1.0
  pro_fraud_evidence: string[];
  pro_customer_argument: string;
  pro_customer_confidence: number; // 0.0 - 1.0
  pro_customer_evidence: string[];
}

// ============================================================================
// Decision Models (backend/app/models/decision.py)
// ============================================================================

export type DecisionType = "APPROVE" | "CHALLENGE" | "BLOCK" | "ESCALATE_TO_HUMAN";

export interface FraudDecision {
  transaction_id: string;
  decision: DecisionType;
  confidence: number; // 0.0 - 1.0
  signals: string[];
  citations_internal: Record<string, unknown>[];
  citations_external: Record<string, unknown>[];
  explanation_customer: string;
  explanation_audit: string;
  agent_trace: string[];
}

export interface ExplanationResult {
  customer_explanation: string;
  audit_explanation: string;
}

// ============================================================================
// Trace Models (backend/app/models/trace.py)
// ============================================================================

export type AgentStatus = "success" | "error" | "timeout" | "skipped";

export interface AgentTraceEntry {
  agent_name: string;
  timestamp: string; // ISO 8601 datetime string
  duration_ms: number;
  input_summary: string;
  output_summary: string;
  status: AgentStatus;
}

// ============================================================================
// Database Models (backend/app/db/models.py)
// ============================================================================

export interface TransactionRecord {
  id: number;
  transaction_id: string;
  raw_data: Transaction;
  decision: DecisionType;
  confidence: number;
  analyzed_at: string; // ISO 8601 datetime string
  created_at: string; // ISO 8601 datetime string
}

export type HITLStatus = "pending" | "resolved";

export interface HITLCase {
  id: number;
  transaction_id: string;
  status: HITLStatus;
  assigned_to: string | null;
  resolution: string | null;
  resolved_at: string | null; // ISO 8601 datetime string
  created_at: string; // ISO 8601 datetime string
}

// ============================================================================
// API Response Models (for frontend consumption)
// ============================================================================

export interface AnalyticsSummary {
  total_analyzed: number;
  decisions_breakdown: Record<DecisionType, number>;
  avg_confidence: number;
  avg_processing_time_ms: number;
  escalation_rate: number;
}

/**
 * Complete transaction analysis for detail page.
 * Returned by enhanced GET /api/v1/transactions/{id}/result
 */
export interface TransactionAnalysisDetail {
  transaction_id: string;
  transaction: Transaction;
  customer_behavior: CustomerBehavior | null;
  transaction_signals: TransactionSignals | null;
  behavioral_signals: BehavioralSignals | null;
  policy_matches: PolicyMatchResult | null;
  threat_intel: ThreatIntelResult | null;
  evidence: AggregatedEvidence | null;
  debate: DebateArguments | null;
  explanation: ExplanationResult | null;
  decision: DecisionType;
  confidence: number;
  analyzed_at: string;
}

// ============================================================================
// WebSocket Models
// ============================================================================

export type WebSocketEventType = "agent_started" | "agent_completed" | "decision_ready";

export interface WebSocketEvent {
  event: WebSocketEventType;
  agent?: string;
  timestamp: string; // ISO 8601 datetime string
  data?: Record<string, unknown>;
}

// ============================================================================
// Type Helpers
// ============================================================================

/**
 * Decision color mapping for UI (as per CLAUDE.md).
 * APPROVE=green, CHALLENGE=amber, BLOCK=red, ESCALATE=violet
 * Hex values for compatibility with recharts and CSS
 */
export const DECISION_COLORS: Record<DecisionType, string> = {
  APPROVE: "#22c55e",        // green-600
  CHALLENGE: "#f59e0b",      // amber-500
  BLOCK: "#ef4444",          // red-600
  ESCALATE_TO_HUMAN: "#8b5cf6" // violet-500
} as const;

/**
 * Risk category color mapping for UI.
 */
export const RISK_COLORS: Record<RiskCategory, string> = {
  low: "green",
  medium: "yellow",
  high: "orange",
  critical: "red",
} as const;
