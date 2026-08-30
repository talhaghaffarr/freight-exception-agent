/**
 * The agent's eligibility ladder, shown as the checks it actually ran.
 *
 * Each row is derived from a fact the API returned, never from a hardcoded
 * "looks good" list, so a check that cannot be evaluated says so instead of
 * showing a tick.
 */

import type { LoadDetail } from "@/app/types";
import { REASON_LABEL, formatClock, humanise, shortReason } from "./facts";

type CheckState = "pass" | "fail" | "hold";

interface Check {
  label: string;
  state: CheckState;
  detail: string;
}

const MARK: Record<CheckState, string> = { pass: "✓", fail: "✕", hold: "" };

export function buildChecks(load: LoadDetail): Check[] {
  const { facts } = load;
  const fresh = facts.tracking_freshness;
  const hasAppointment = facts.appointment_start !== null;

  return [
    {
      label: "Pickup open",
      state: facts.reason === "pickup_complete" ? "fail" : "pass",
      detail: facts.reason === "pickup_complete" ? "completed" : "not completed",
    },
    {
      label: "Appointment on file",
      state: hasAppointment ? "pass" : "fail",
      detail: hasAppointment
        ? `${formatClock(facts.appointment_start)} · rev ${facts.appointment_revision}`
        : "none",
    },
    {
      label: "Tracking fresh",
      state: fresh === "stale" || fresh === null ? "fail" : "pass",
      detail: fresh === null ? "no position" : `latest fix ${fresh}`,
    },
    {
      label: "ETA computed",
      state: facts.eta.available ? "pass" : "fail",
      detail: facts.eta.available
        ? `${formatClock(facts.eta.predicted_arrival)} · ${humanise(facts.eta.source)}`
        : (REASON_LABEL[facts.eta.reason ?? ""] ?? "unavailable"),
    },
    {
      label: `Threshold exceeded`,
      state:
        facts.minutes_late === null
          ? "hold"
          : facts.minutes_late >= facts.threshold_minutes
            ? "pass"
            : "fail",
      detail:
        facts.minutes_late === null
          ? "no ETA"
          : `${facts.minutes_late} min vs ${facts.threshold_minutes} min`,
    },
    {
      label: "Recipient verified",
      state: load.account_manager.email ? "pass" : "fail",
      detail: load.account_manager.email || "none",
    },
    {
      label: "No prior action",
      state: load.goals.length === 0 ? "pass" : "fail",
      detail:
        load.goals.length === 0
          ? "nothing sent for this appointment"
          : `${load.goals.length} open`,
    },
  ];
}

export function AgentDecision({ load }: { load: LoadDetail }) {
  const checks = buildChecks(load);
  const blocking = checks.filter((check) => check.state === "fail");
  const wouldAct = blocking.length === 0;
  const reason = shortReason(load.facts);

  return (
    <section className="decision" aria-label="Agent decision">
      <header className="decision__head">
        <h3 className="decision__title">Agent decision</h3>
        <span className={`chip chip--${wouldAct ? "late" : "unknown"}`}>
          {wouldAct ? "Ready" : "Held"}
        </span>
      </header>

      <ul className="checks">
        {checks.map((check) => (
          <li key={check.label} className={`check check--${check.state}`}>
            <span className="check__mark" aria-hidden="true">
              {MARK[check.state]}
            </span>
            <span>
              <span className="check__label">{check.label}</span>
              <span className="check__detail">{check.detail}</span>
            </span>
          </li>
        ))}
      </ul>

      <p className={`decision__next${wouldAct ? "" : " decision__next--held"}`}>
        {wouldAct ? (
          <>
            <b>Next</b> · enqueue one deduplicated notification
          </>
        ) : (
          <>
            <b>Suppressed</b> · {reason ?? `${blocking.length} checks failed`}
          </>
        )}
      </p>
    </section>
  );
}
