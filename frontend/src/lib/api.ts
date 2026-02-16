/**
 * Centralized API client for fraud detection backend.
 * All API calls go through this module for consistent error handling and typing.
 */

import {
  Transaction,
  CustomerBehavior,
  FraudDecision,
  TransactionRecord,
  TransactionAnalysisDetail,
  AgentTraceEntry,
  HITLCase,
  AnalyticsSummary,
  AnalyzeStartResponse,
  Policy,
  PolicyCreate,
  PolicyUpdate,
} from "@/lib/types";

// API base URL from environment variables
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Custom error class for API errors with status code and message.
 */
export class APIError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Generic fetch wrapper with error handling and JSON parsing.
 */
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const config: RequestInit = {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);

    // Handle non-2xx responses
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorData: unknown;

      try {
        errorData = await response.json();
        if (errorData && typeof errorData === "object" && "detail" in errorData) {
          errorMessage = String(errorData.detail);
        }
      } catch {
        // If JSON parsing fails, use default error message
      }

      throw new APIError(response.status, errorMessage, errorData);
    }

    // Parse and return JSON response
    const data = await response.json();
    return data as T;
  } catch (error) {
    // Re-throw APIError as-is
    if (error instanceof APIError) {
      throw error;
    }

    // Wrap network errors
    if (error instanceof TypeError) {
      throw new APIError(0, `Network error: ${error.message}`);
    }

    // Wrap unknown errors
    throw new APIError(
      500,
      error instanceof Error ? error.message : "Unknown error occurred"
    );
  }
}

// ============================================================================
// Transaction Analysis API
// ============================================================================

/**
 * Analyze a transaction for fraud.
 * POST /api/v1/transactions/analyze
 */
export async function analyzeTransaction(
  transaction: Transaction,
  customerBehavior: CustomerBehavior
): Promise<FraudDecision> {
  return fetchAPI<FraudDecision>("/api/v1/transactions/analyze", {
    method: "POST",
    body: JSON.stringify({
      transaction,
      customer_behavior: customerBehavior,
    }),
  });
}

/**
 * Start a transaction analysis in the background (fire-and-forget).
 * POST /api/v1/transactions/analyze/start
 * Returns 202 immediately; progress is streamed via WebSocket.
 */
export async function startAnalysis(
  transaction: Transaction,
  customerBehavior: CustomerBehavior
): Promise<AnalyzeStartResponse> {
  return fetchAPI<AnalyzeStartResponse>("/api/v1/transactions/analyze/start", {
    method: "POST",
    body: JSON.stringify({
      transaction,
      customer_behavior: customerBehavior,
    }),
  });
}

/**
 * Get list of analyzed transactions with pagination.
 * GET /api/v1/transactions
 */
export async function getTransactions(
  limit?: number,
  offset?: number
): Promise<TransactionRecord[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.append("limit", limit.toString());
  if (offset !== undefined) params.append("offset", offset.toString());

  const query = params.toString();
  const endpoint = `/api/v1/transactions${query ? `?${query}` : ""}`;

  return fetchAPI<TransactionRecord[]>(endpoint);
}

/**
 * Get complete analysis detail for a specific transaction.
 * GET /api/v1/transactions/{id}/result
 */
export async function getTransactionDetail(
  transactionId: string
): Promise<TransactionAnalysisDetail> {
  return fetchAPI<TransactionAnalysisDetail>(
    `/api/v1/transactions/${transactionId}/result`
  );
}

/**
 * Get agent execution trace for a specific transaction.
 * GET /api/v1/transactions/{id}/trace
 */
export async function getTransactionTrace(
  transactionId: string
): Promise<AgentTraceEntry[]> {
  return fetchAPI<AgentTraceEntry[]>(
    `/api/v1/transactions/${transactionId}/trace`
  );
}

// ============================================================================
// Human-in-the-Loop (HITL) API
// ============================================================================

/**
 * Get pending HITL cases requiring human review.
 * GET /api/v1/hitl/queue
 */
export async function getHITLQueue(): Promise<HITLCase[]> {
  return fetchAPI<HITLCase[]>("/api/v1/hitl/queue?status=pending");
}

/**
 * Resolve a HITL case with human decision.
 * POST /api/v1/hitl/{id}/resolve
 */
export async function resolveHITLCase(
  caseId: number,
  resolution: "APPROVE" | "BLOCK",
  reason: string
): Promise<HITLCase> {
  return fetchAPI<HITLCase>(`/api/v1/hitl/${caseId}/resolve`, {
    method: "POST",
    body: JSON.stringify({
      resolution,
      reason,
    }),
  });
}

// ============================================================================
// Analytics API
// ============================================================================

/**
 * Get analytics summary for the dashboard.
 * GET /api/v1/analytics/summary
 */
export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return fetchAPI<AnalyticsSummary>("/api/v1/analytics/summary");
}

// ============================================================================
// Policy Management API
// ============================================================================

/**
 * Get list of all fraud detection policies.
 * GET /api/v1/policies
 */
export async function getPolicies(): Promise<Policy[]> {
  return fetchAPI<Policy[]>("/api/v1/policies");
}

/**
 * Get a single policy by ID.
 * GET /api/v1/policies/{id}
 */
export async function getPolicy(policyId: string): Promise<Policy> {
  return fetchAPI<Policy>(`/api/v1/policies/${policyId}`);
}

/**
 * Create a new policy.
 * POST /api/v1/policies
 */
export async function createPolicy(policy: PolicyCreate): Promise<Policy> {
  return fetchAPI<Policy>("/api/v1/policies", {
    method: "POST",
    body: JSON.stringify(policy),
  });
}

/**
 * Update an existing policy.
 * PUT /api/v1/policies/{id}
 */
export async function updatePolicy(
  policyId: string,
  updates: PolicyUpdate
): Promise<Policy> {
  return fetchAPI<Policy>(`/api/v1/policies/${policyId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

/**
 * Delete a policy.
 * DELETE /api/v1/policies/{id}
 */
export async function deletePolicy(policyId: string): Promise<void> {
  return fetchAPI<void>(`/api/v1/policies/${policyId}`, {
    method: "DELETE",
  });
}

/**
 * Manually trigger ChromaDB reingest of all policies.
 * POST /api/v1/policies/reingest
 */
export async function reingestPolicies(): Promise<void> {
  return fetchAPI<void>("/api/v1/policies/reingest", {
    method: "POST",
  });
}

// ============================================================================
// Health Check API
// ============================================================================

/**
 * Health check endpoint.
 * GET /api/v1/health
 */
export async function healthCheck(): Promise<{ status: string }> {
  return fetchAPI<{ status: string }>("/api/v1/health");
}
