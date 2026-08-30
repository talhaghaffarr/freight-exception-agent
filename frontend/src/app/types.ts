/** Wire types shared by the console. Mirrors the Flask `{data, meta, error}` envelope. */

export type EnvironmentMode = "sandbox" | "allowlist" | "live";

export type HealthStatus = "healthy" | "degraded" | "unhealthy" | "unknown";

export type Role =
  | "platform_operator"
  | "brokerage_admin"
  | "account_manager"
  | "reviewer";

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  timezone: string;
}

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  is_platform_operator: boolean;
}

export interface Session {
  user: SessionUser;
  tenants: Tenant[];
  roles: Record<string, Role | string>;
  environment_mode: EnvironmentMode;
}

export interface ComponentHealth {
  name: string;
  status: HealthStatus;
  required: boolean;
  detail: string | null;
  latency_ms: number;
  checked_at: string;
  metadata: Record<string, unknown>;
}

export interface HealthReport {
  status: HealthStatus;
  ready: boolean;
  checked_at: string;
  components: ComponentHealth[];
}

export interface DashboardAgentRow {
  agent_type: string;
  version: string;
  tenant_slug: string;
  enabled: boolean;
  goals_open: number;
  success_rate: number | null;
}

export interface Dashboard {
  agents: DashboardAgentRow[];
  goals: { opened: number; waiting: number; needs_review: number; failed: number };
  communications: { email: number; sms: number; voice: number };
  value: { operator_minutes_saved: number };
  recent_activity: Array<{
    id: string;
    occurred_at: string;
    summary: string;
    goal_id: string | null;
  }>;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: { request_id: string };
  error: { code: string; message: string; details: Record<string, unknown> } | null;
}
