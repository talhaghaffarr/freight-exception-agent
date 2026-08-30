/**
 * Operator language for the goal machinery.
 *
 * The wire carries stable enum values; the console speaks dispatcher. A raw
 * enum is rendered only as secondary evidence (mono, beside the human label),
 * never as the primary copy.
 */

export const STATE_LABEL: Record<string, string> = {
  opened: "Opened",
  collecting_facts: "Collecting facts",
  evaluating: "Evaluating",
  action_pending: "Action pending",
  executing: "Sending",
  waiting: "Waiting",
  needs_review: "Needs review",
  succeeded: "Succeeded",
  suppressed: "Suppressed",
  failed: "Failed",
  expired: "Expired",
};

/** Chip chroma discipline: colour only where it demands a person's attention. */
export type StateTone = "critical" | "warning" | "positive" | "neutral" | "info";

export function stateTone(state: string): StateTone {
  if (state === "needs_review" || state === "failed") return "critical";
  if (state === "waiting") return "warning";
  if (state === "succeeded") return "positive";
  if (state === "suppressed" || state === "expired") return "neutral";
  return "info";
}

export const OUTCOME_LABEL: Record<string, string> = {
  acted_successfully: "Acted successfully",
  action_delivery_unknown: "Delivery unknown",
  provider_retry_scheduled: "Retry scheduled",
  provider_attempts_exhausted: "Attempts exhausted",
  tenant_disabled: "Disabled for tenant",
  agent_disabled: "Agent disabled",
  outside_schedule: "Outside send window",
  below_threshold: "Below threshold",
  already_open_goal: "Already open",
  already_notified: "Already notified",
  facts_incomplete: "Facts incomplete",
  facts_contradictory: "Facts contradictory",
  tracking_stale: "Tracking stale",
  load_not_found: "Load not found",
  sender_unverified: "Sender unverified",
  sender_not_enrolled: "Sender not enrolled",
  tenant_ambiguous: "Tenant ambiguous",
  rate_limited: "Rate limited",
  loop_suppressed: "Loop suppressed",
  intent_unsupported: "Intent unsupported",
  reference_ambiguous: "Reference ambiguous",
  expired_without_action: "Expired without action",
  operator_suppressed: "Suppressed by operator",
};

export function humanize(value: string): string {
  const words = value.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function outcomeLabel(outcome: string): string {
  return OUTCOME_LABEL[outcome] ?? humanize(outcome);
}

export const AGENT_LABEL: Record<string, string> = {
  late_pickup: "Late Pickup Alert",
  reactive_status_email: "Reactive Status Email",
  pod_collection: "POD Collection",
  eta_confirmation: "ETA Confirmation",
  detention_risk: "Detention Risk",
};

export function agentLabel(agentType: string): string {
  return AGENT_LABEL[agentType] ?? humanize(agentType);
}

/** What actually happened at each step, in the operator's words. */
export const EVENT_LABEL: Record<string, string> = {
  opened: "Goal opened",
  collecting_facts: "Facts collected",
  evaluating: "Evaluated against threshold",
  action_enqueued: "Action enqueued",
  action_executing: "Sending notification",
  waiting: "Waiting",
  needs_review: "Flagged for review",
  outcome_recorded: "Outcome recorded",
};

export function eventLabel(eventType: string): string {
  return EVENT_LABEL[eventType] ?? humanize(eventType);
}

export function formatStamp(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  const day = date.toLocaleDateString([], { month: "short", day: "numeric" });
  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${day} ${time}`;
}
