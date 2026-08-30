/**
 * A status chip.
 *
 * Colour is an accelerator, never the message: the badge always renders the
 * status name, so the meaning survives greyscale, colour-blindness, and a
 * screen reader.
 */

import "./StatusBadge.css";

export type Tone = "positive" | "warning" | "critical" | "info" | "neutral" | "model";

const TONE_BY_STATUS: Record<string, Tone> = {
  // Component health
  healthy: "positive",
  degraded: "warning",
  unhealthy: "critical",
  unknown: "neutral",
  // Goal states
  opened: "info",
  collecting_facts: "info",
  evaluating: "info",
  action_pending: "info",
  executing: "info",
  succeeded: "positive",
  waiting: "warning",
  needs_review: "warning",
  suppressed: "neutral",
  expired: "neutral",
  failed: "critical",
  // Delivery
  delivered: "positive",
  delivery_unknown: "warning",
  bounced: "critical",
  blocked: "critical",
  // Environment
  sandbox: "info",
  allowlist: "warning",
  live: "critical",
};

export function humanizeStatus(status: string): string {
  const spaced = status.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function toneFor(status: string): Tone {
  return TONE_BY_STATUS[status] ?? "neutral";
}

export interface StatusBadgeProps {
  status: string;
  label?: string;
  title?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, label, title, size = "md" }: StatusBadgeProps) {
  const tone = toneFor(status);
  return (
    <span
      className="status-badge"
      data-tone={tone}
      data-size={size}
      data-testid={`status-${status}`}
      title={title}
    >
      <span className="status-badge__dot" aria-hidden="true" />
      {label ?? humanizeStatus(status)}
    </span>
  );
}
