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
  /** Always carries `request_id`; resources add their own keys alongside it. */
  meta: { request_id: string } & Record<string, unknown>;
  error: { code: string; message: string; details: Record<string, unknown> } | null;
}

/**
 * Live operations.
 *
 * `eta.predicted_arrival` is null whenever the fact engine declined to compute
 * one, and `eta.reason` says why. The UI must render the reason rather than an
 * empty slot, so these fields are deliberately nullable rather than optional.
 */
export type LateClassification =
  | "late"
  | "at_risk"
  | "on_time"
  | "early"
  | "scheduled"
  | "unknown";
export type TrackingFreshness = "fresh" | "aging" | "stale";

export interface EtaFact {
  available: boolean;
  predicted_arrival: string | null;
  reason: string | null;
  source: string | null;
  traffic_assumption: string | null;
  remaining_meters: number | null;
}

export interface LateFacts {
  classification: LateClassification;
  minutes_late: number | null;
  threshold_minutes: number;
  reason: string | null;
  appointment_start: string | null;
  appointment_revision: number | null;
  tracking_freshness: TrackingFreshness | null;
  evidence_at: string | null;
  position: GeoPoint | null;
  eta: EtaFact;
}

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface BoardRow {
  load_id: string;
  reference: string;
  customer_name: string;
  carrier_name: string | null;
  driver_name: string | null;
  origin: string;
  destination: string;
  origin_point: GeoPoint | null;
  destination_point: GeoPoint | null;
  pickup_appointment: string | null;
  facts: LateFacts;
}

export interface BoardSummary {
  active_loads: number;
  needs_action: number;
  late_pickup: number;
  at_risk: number;
  no_signal: number;
  on_track: number;
  not_started: number;
}

export interface BoardResponse {
  rows: BoardRow[];
  summary: BoardSummary;
  generatedAt: string | null;
}

export interface GoalSummary {
  id: string;
  state: string;
  agent_type: string;
  agent_version: string;
  trigger_fingerprint: string;
  terminal_outcome: string | null;
  opened_at: string | null;
}

export interface LoadDetail extends BoardRow {
  account_manager: { name: string | null; email: string };
  pickup_facility: string | null;
  goals: GoalSummary[];
}

export interface RaceAttempt {
  worker: string;
  created: boolean;
  outcome: "inserted" | "unique_conflict";
  goal_id: string;
  duration_ms: number;
}

export interface RaceResult {
  reference: string;
  trigger_fingerprint: string;
  goals_created: number;
  opened_events: number;
  duplicates_prevented: number;
  constraint: string;
  attempts: RaceAttempt[];
}

export interface GoalTraceEvent {
  sequence: number;
  event_type: string;
  from_state: string | null;
  to_state: string | null;
  detail: Record<string, unknown>;
  occurred_at: string | null;
}

export interface GoalTrace {
  goal: GoalSummary;
  events: GoalTraceEvent[];
}
