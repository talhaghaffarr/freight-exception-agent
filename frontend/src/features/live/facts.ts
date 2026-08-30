/**
 * Presentation helpers for computed facts.
 *
 * The single rule these enforce: an unknown is rendered as a named unknown.
 * No helper here ever returns an empty string or a zero to stand in for a
 * value the fact engine declined to compute.
 */

import type { BoardRow, LateClassification, LateFacts } from "@/app/types";

export const CLASSIFICATION_LABEL: Record<LateClassification, string> = {
  late: "Late pickup",
  at_risk: "At risk",
  on_time: "On time",
  early: "Early",
  scheduled: "Not started",
  unknown: "ETA unknown",
};

/** Why the engine refused to compute, in the operator's language. */
export const REASON_LABEL: Record<string, string> = {
  tracking_stale: "Tracking stale",
  tracking_missing: "No position reported",
  route_unavailable: "No route estimate",
  appointment_missing: "No appointment",
  pickup_complete: "Pickup complete",
  facts_incomplete: "Facts incomplete",
};

export const FRESHNESS_LABEL: Record<string, string> = {
  fresh: "Fresh",
  aging: "Aging",
  stale: "Stale",
};

export function formatClock(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatAge(iso: string | null, now: number = Date.now()): string {
  if (!iso) return "no signal";
  const minutes = Math.round((now - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m ago`;
}

/** Signed lateness, e.g. `+38 min` or `-7 min`, or a named unknown. */
export function formatLateness(facts: LateFacts): string {
  if (facts.minutes_late === null) return "unknown";
  const sign = facts.minutes_late > 0 ? "+" : "";
  return `${sign}${facts.minutes_late} min`;
}

export function shortReason(facts: LateFacts): string | null {
  const reason = facts.reason ?? facts.eta.reason;
  return reason ? (REASON_LABEL[reason] ?? reason) : null;
}

/** A compact badge caption used in the priority list. */
export function rowBadge(row: BoardRow): string {
  const { facts } = row;
  if (facts.classification === "unknown") {
    return facts.eta.reason === "tracking_missing" ? "No signal" : "ETA unknown";
  }
  if (facts.minutes_late !== null && facts.minutes_late > 0) {
    return `+${facts.minutes_late} min`;
  }
  return CLASSIFICATION_LABEL[facts.classification];
}
