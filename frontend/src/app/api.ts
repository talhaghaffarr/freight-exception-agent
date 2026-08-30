/**
 * The single place that talks to the Flask API.
 *
 * Errors are surfaced with the server's stable `code`, so screens can branch on
 * a contract rather than on a message string.
 */

import type { ApiEnvelope, Dashboard, HealthReport, Session } from "./types";

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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
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
  return envelope.data;
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
};

export { request };
