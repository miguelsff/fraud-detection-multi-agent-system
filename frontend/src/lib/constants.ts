/**
 * Centralized constants for the fraud detection system.
 * All color schemes, mappings, and configurations should be defined here.
 */

import {
  Search,
  TrendingUp,
  BookOpen,
  Shield,
  Layers,
  AlertTriangle,
  UserCheck,
  Scale,
  FileText,
  type LucideIcon,
} from "lucide-react";
import type { DecisionType, RiskCategory } from "./types";

// ============================================================================
// Decision Constants
// ============================================================================

/**
 * Color mapping for fraud decisions (Tailwind colors as hex).
 * Used consistently across all UI components.
 */
export const DECISION_COLORS: Record<DecisionType, string> = {
  APPROVE: "#22c55e",        // green-600
  CHALLENGE: "#f59e0b",      // amber-500
  BLOCK: "#ef4444",          // red-600
  ESCALATE_TO_HUMAN: "#8b5cf6" // violet-500
} as const;

/**
 * Human-readable labels for fraud decisions.
 */
export const DECISION_LABELS: Record<DecisionType, string> = {
  APPROVE: "Approved",
  CHALLENGE: "Challenged",
  BLOCK: "Blocked",
  ESCALATE_TO_HUMAN: "Escalated to Human"
} as const;

/**
 * Decision descriptions for tooltips/help text.
 */
export const DECISION_DESCRIPTIONS: Record<DecisionType, string> = {
  APPROVE: "Transaction approved - no fraud risk detected",
  CHALLENGE: "Transaction requires additional verification (e.g., 2FA, SMS code)",
  BLOCK: "Transaction blocked - high fraud risk detected",
  ESCALATE_TO_HUMAN: "Ambiguous case - requires human review"
} as const;

// ============================================================================
// Risk Category Constants
// ============================================================================

/**
 * Color mapping for risk categories (Tailwind color names).
 * Used for badges and visual indicators.
 */
export const RISK_COLORS: Record<RiskCategory, string> = {
  low: "green",
  medium: "amber",
  high: "orange",
  critical: "red",
} as const;

/**
 * Risk category labels.
 */
export const RISK_LABELS: Record<RiskCategory, string> = {
  low: "Low Risk",
  medium: "Medium Risk",
  high: "High Risk",
  critical: "Critical Risk",
} as const;

/**
 * Risk score thresholds (0-100 scale).
 */
export const RISK_THRESHOLDS = {
  low: { min: 0, max: 25 },
  medium: { min: 25, max: 50 },
  high: { min: 50, max: 75 },
  critical: { min: 75, max: 100 },
} as const;

// ============================================================================
// Agent Constants
// ============================================================================

/**
 * Agent name type - all possible agent names in the system.
 */
export type AgentName =
  | "TransactionContext"
  | "BehavioralPattern"
  | "PolicyRAG"
  | "ExternalThreat"
  | "EvidenceAggregation"
  | "ProFraud"
  | "ProCustomer"
  | "DecisionArbiter"
  | "Explainability";

/**
 * Icon mapping for each agent (Lucide icons).
 */
export const AGENT_ICONS: Record<AgentName, LucideIcon> = {
  TransactionContext: Search,
  BehavioralPattern: TrendingUp,
  PolicyRAG: BookOpen,
  ExternalThreat: Shield,
  EvidenceAggregation: Layers,
  ProFraud: AlertTriangle,
  ProCustomer: UserCheck,
  DecisionArbiter: Scale,
  Explainability: FileText,
} as const;

/**
 * Phase mapping for each agent (1-5).
 * Phase 1: Parallel Collection
 * Phase 2: Consolidation
 * Phase 3: Adversarial Debate
 * Phase 4: Decision
 * Phase 5: Explanation
 */
export const AGENT_PHASES: Record<AgentName, number> = {
  TransactionContext: 1,
  BehavioralPattern: 1,
  PolicyRAG: 1,
  ExternalThreat: 1,
  EvidenceAggregation: 2,
  ProFraud: 3,
  ProCustomer: 3,
  DecisionArbiter: 4,
  Explainability: 5,
} as const;

/**
 * Agent display names (human-readable).
 */
export const AGENT_LABELS: Record<AgentName, string> = {
  TransactionContext: "Transaction Context",
  BehavioralPattern: "Behavioral Pattern",
  PolicyRAG: "Policy RAG",
  ExternalThreat: "External Threat Intel",
  EvidenceAggregation: "Evidence Aggregation",
  ProFraud: "Pro-Fraud Advocate",
  ProCustomer: "Pro-Customer Advocate",
  DecisionArbiter: "Decision Arbiter",
  Explainability: "Explainability",
} as const;

/**
 * Agent descriptions for tooltips.
 */
export const AGENT_DESCRIPTIONS: Record<AgentName, string> = {
  TransactionContext: "Analyzes transaction metadata and flags anomalies",
  BehavioralPattern: "Compares transaction against customer's historical behavior",
  PolicyRAG: "Retrieves relevant fraud policies from knowledge base",
  ExternalThreat: "Queries external threat intelligence sources",
  EvidenceAggregation: "Consolidates all signals into composite risk score",
  ProFraud: "Argues the case for fraud detection",
  ProCustomer: "Argues the case for legitimate transaction",
  DecisionArbiter: "Evaluates debate and makes final decision",
  Explainability: "Generates customer-facing and audit explanations",
} as const;

// ============================================================================
// Phase Constants
// ============================================================================

/**
 * Pipeline phase configuration.
 */
export const PIPELINE_PHASES = [
  {
    id: 1,
    name: "Fase 1 — Recolección",
    nameEn: "Phase 1 — Collection",
    isParallel: true,
    color: "border-blue-500",
    description: "Parallel data collection from multiple sources",
  },
  {
    id: 2,
    name: "Fase 2 — Consolidación",
    nameEn: "Phase 2 — Consolidation",
    isParallel: false,
    color: "border-purple-500",
    description: "Evidence aggregation and risk scoring",
  },
  {
    id: 3,
    name: "Fase 3 — Deliberación",
    nameEn: "Phase 3 — Deliberation",
    isParallel: true,
    color: "border-orange-500",
    description: "Adversarial debate between pro-fraud and pro-customer agents",
  },
  {
    id: 4,
    name: "Fase 4 — Decisión",
    nameEn: "Phase 4 — Decision",
    isParallel: false,
    color: "border-green-500",
    description: "Arbiter evaluates debate and makes final decision",
  },
  {
    id: 5,
    name: "Fase 5 — Explicación",
    nameEn: "Phase 5 — Explanation",
    isParallel: false,
    color: "border-gray-500",
    description: "Generate customer-facing and audit explanations",
  },
] as const;

// ============================================================================
// UI Constants
// ============================================================================

/**
 * Confidence level color mapping (for badges).
 */
export const CONFIDENCE_COLORS = {
  veryLow: "bg-red-500",      // 0-20%
  low: "bg-orange-500",       // 20-40%
  medium: "bg-amber-500",     // 40-60%
  high: "bg-blue-500",        // 60-80%
  veryHigh: "bg-green-500",   // 80-100%
} as const;

/**
 * Get confidence color based on value (0-1).
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence < 0.2) return CONFIDENCE_COLORS.veryLow;
  if (confidence < 0.4) return CONFIDENCE_COLORS.low;
  if (confidence < 0.6) return CONFIDENCE_COLORS.medium;
  if (confidence < 0.8) return CONFIDENCE_COLORS.high;
  return CONFIDENCE_COLORS.veryHigh;
}

/**
 * Processing time thresholds (in milliseconds).
 */
export const PROCESSING_TIME_THRESHOLDS = {
  fast: 5000,      // < 5s = excellent
  target: 10000,   // < 10s = acceptable
  slow: 15000,     // > 15s = needs optimization
} as const;

/**
 * Blocked percentage color thresholds (for risk by country).
 */
export const BLOCKED_PERCENTAGE_THRESHOLDS = {
  low: 10,      // 0-10% = green
  medium: 25,   // 10-25% = amber
  high: 50,     // 25-50% = orange
  // > 50% = red
} as const;

// ============================================================================
// API Constants
// ============================================================================

/**
 * Default pagination limits.
 */
export const PAGINATION = {
  defaultLimit: 100,
  maxLimit: 1000,
  defaultOffset: 0,
} as const;

/**
 * Polling/refresh intervals (in seconds).
 */
export const REFRESH_INTERVALS = {
  transactions: 30,     // Transaction list auto-refresh
  dashboard: 60,        // Dashboard stats refresh
  hitl: 15,            // HITL queue refresh (more frequent)
  analytics: 120,      // Analytics refresh (less frequent)
} as const;

/**
 * WebSocket reconnect delays (in milliseconds).
 */
export const WEBSOCKET_RECONNECT = {
  initialDelay: 1000,
  maxDelay: 30000,
  multiplier: 2,
} as const;

// ============================================================================
// Validation Constants
// ============================================================================

/**
 * Transaction amount limits (in base currency).
 */
export const AMOUNT_LIMITS = {
  min: 0.01,
  max: 1000000,
  suspicious: 10000, // Amount that triggers extra scrutiny
} as const;

/**
 * Confidence score bounds.
 */
export const CONFIDENCE_BOUNDS = {
  min: 0,
  max: 1,
} as const;

// ============================================================================
// Export All
// ============================================================================

export const CONSTANTS = {
  DECISION_COLORS,
  DECISION_LABELS,
  DECISION_DESCRIPTIONS,
  RISK_COLORS,
  RISK_LABELS,
  RISK_THRESHOLDS,
  AGENT_ICONS,
  AGENT_PHASES,
  AGENT_LABELS,
  AGENT_DESCRIPTIONS,
  PIPELINE_PHASES,
  CONFIDENCE_COLORS,
  PROCESSING_TIME_THRESHOLDS,
  BLOCKED_PERCENTAGE_THRESHOLDS,
  PAGINATION,
  REFRESH_INTERVALS,
  WEBSOCKET_RECONNECT,
  AMOUNT_LIMITS,
  CONFIDENCE_BOUNDS,
} as const;
