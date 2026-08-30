/**
 * The single place that talks to the Flask API.
 *
 * Errors are surfaced with the server's stable `code`, so screens can branch on
 * a contract rather than on a message string.
 */

import type {
  AgentCatalogEntry,
  ApiEnvelope,
  BoardResponse,
  Dashboard,
  GoalListResponse,
  GoalRow,
  GoalTrace,
  HealthReport,
  LoadDetail,
  OutcomeAnalytics,
  RaceResult,
  Session,
} from "./types";

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details: Record<string, unknown> = {},
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function requestEnvelope<T>(
  path: string,
  init: RequestInit = {},
): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
    ...init,
  });

  let envelope: ApiEnvelope<T> | null = null;
  try {
    envelope = (await response.json()) as ApiEnvelope<T>;
  } catch {
    envelope = null;
  }

  if (!response.ok || envelope?.error) {
    const error = envelope?.error;
    throw new ApiError(
      error?.code ?? "UNEXPECTED_ERROR",
      error?.message ?? `Request to ${path} failed.`,
      response.status,
      error?.details ?? {},
      envelope?.meta?.request_id,
    );
  }

  if (!envelope) {
    throw new ApiError("MALFORMED_RESPONSE", `${path} did not return JSON.`, response.status);
  }
  return envelope;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  return (await requestEnvelope<T>(path, init)).data;
}

export const api = {
  me: () => request<Session>("/auth/me"),
  signIn: (email: string) =>
    request<Session>("/auth/demo-session", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  signOut: () => request<{ signed_out: boolean }>("/auth/sign-out", { method: "POST" }),
  health: () => request<HealthReport>("/system/health"),
  dashboard: (tenantSlug: string | null) =>
    request<Dashboard>(
      `/dashboard${tenantSlug && tenantSlug !== "all" ? `?tenant=${encodeURIComponent(tenantSlug)}` : ""}`,
    ),
  loads: async (tenantSlug: string): Promise<BoardResponse> => {
    const envelope = await requestEnvelope<BoardResponse["rows"]>(
      `/tenants/${encodeURIComponent(tenantSlug)}/loads`,
    );
    return {
      rows: envelope.data,
      summary: envelope.meta?.summary as BoardResponse["summary"],
      generatedAt: (envelope.meta?.generated_at as string) ?? null,
    };
  },
  load: (tenantSlug: string, reference: string) =>
    request<LoadDetail>(
      `/tenants/${encodeURIComponent(tenantSlug)}/loads/${encodeURIComponent(reference)}`,
    ),
  raceScanners: (tenantSlug: string, reference: string) =>
    request<RaceResult>(`/tenants/${encodeURIComponent(tenantSlug)}/demo/race`, {
      method: "POST",
      body: JSON.stringify({ reference }),
    }),
  resetDemo: (tenantSlug: string) =>
    request<{ goals_cleared: number; loads_reseeded: number }>(
      `/tenants/${encodeURIComponent(tenantSlug)}/demo/reset`,
      { method: "POST", body: JSON.stringify({}) },
    ),
  goalTrace: (tenantSlug: string, goalId: string) =>
    request<GoalTrace>(
      `/tenants/${encodeURIComponent(tenantSlug)}/goals/${encodeURIComponent(goalId)}/trace`,
    ),
  listGoals: async (
    tenantSlug: string,
    options: { state?: string | null; agentType?: string | null; limit?: number } = {},
  ): Promise<GoalListResponse> => {
    const params = new URLSearchParams();
    if (options.state) params.set("state", options.state);
    if (options.agentType) params.set("agent_type", options.agentType);
    if (options.limit) params.set("limit", String(options.limit));
    const query = params.toString();
    const envelope = await requestEnvelope<GoalRow[]>(
      `/tenants/${encodeURIComponent(tenantSlug)}/goals${query ? `?${query}` : ""}`,
    );
    return {
      rows: envelope.data,
      counts: (envelope.meta?.counts as Record<string, number>) ?? {},
    };
  },
  agentCatalog: (tenantSlug: string) =>
    request<AgentCatalogEntry[]>(`/tenants/${encodeURIComponent(tenantSlug)}/agents/catalog`),
  outcomeAnalytics: (tenantSlug: string, days = 7) =>
    request<OutcomeAnalytics>(
      `/tenants/${encodeURIComponent(tenantSlug)}/analytics/outcomes?days=${days}`,
    ),
};

export { request };
