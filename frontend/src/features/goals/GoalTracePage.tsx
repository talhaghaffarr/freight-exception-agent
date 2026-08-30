/**
 * One goal's full story, event by event.
 *
 * The spine reads top to bottom like a recorder trace: what the agent saw,
 * what it decided, and how the episode ended. The trigger fingerprint is shown
 * as under-the-hood proof — it is the database key that made a duplicate of
 * this goal impossible.
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/app/api";
import { useSession } from "@/app/session";
import type { GoalTraceEvent } from "@/app/types";
import { StateChip } from "./GoalsPage";
import { agentLabel, eventLabel, formatStamp, outcomeLabel } from "./labels";
import "./Goals.css";

function DetailFacts({ detail }: { detail: Record<string, unknown> }) {
  const entries = Object.entries(detail);
  if (entries.length === 0) return null;
  return (
    <p className="traceevent__detail">
      {entries.map(([key, value]) => (
        <span key={key} className="traceevent__fact">
          <b>{key}:</b> {typeof value === "string" ? value : JSON.stringify(value)}
        </span>
      ))}
    </p>
  );
}

function TraceEvent({ event, terminal }: { event: GoalTraceEvent; terminal: boolean }) {
  return (
    <li className={`traceevent${terminal ? " traceevent--terminal" : ""}`}>
      <span className="traceevent__seq" aria-hidden="true">
        {event.sequence}
      </span>
      <div>
        <div className="traceevent__head">
          <span className="traceevent__label">{eventLabel(event.event_type)}</span>
          <span className="traceevent__type">{event.event_type}</span>
          {event.to_state ? (
            <span className="traceevent__states">
              {event.from_state ? `${event.from_state} → ` : ""}
              {event.to_state}
            </span>
          ) : null}
          <time className="traceevent__time" dateTime={event.occurred_at ?? undefined}>
            {formatStamp(event.occurred_at)}
          </time>
        </div>
        <DetailFacts detail={event.detail} />
      </div>
    </li>
  );
}

export function GoalTracePage() {
  const { goalId } = useParams<{ goalId: string }>();
  const { activeTenantSlug, session } = useSession();
  const tenantSlug =
    activeTenantSlug && activeTenantSlug !== "all"
      ? activeTenantSlug
      : (session?.tenants[0]?.slug ?? null);

  const [copied, setCopied] = useState(false);

  const traceQuery = useQuery({
    queryKey: ["goal-trace", tenantSlug, goalId],
    queryFn: () => api.goalTrace(tenantSlug as string, goalId as string),
    enabled: Boolean(tenantSlug && goalId),
  });

  if (!tenantSlug || !goalId) {
    return <p className="goals__empty">Select a tenant and a goal to see its trace.</p>;
  }

  if (traceQuery.isPending) {
    return <p className="goals__empty">Reading the event trace…</p>;
  }
  if (traceQuery.isError) {
    return (
      <div className="trace">
        <Link to="/goals" className="trace__back">
          ← Goals
        </Link>
        <p className="goals__empty">{(traceQuery.error as Error).message}</p>
      </div>
    );
  }

  const { goal, events } = traceQuery.data;

  const copyFingerprint = async () => {
    try {
      await navigator.clipboard.writeText(goal.trigger_fingerprint);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* Clipboard access denied: the value stays selectable by hand. */
    }
  };

  return (
    <div className="trace">
      <Link to="/goals" className="trace__back">
        ← Goals
      </Link>

      <header className="trace__lede">
        <div>
          <h1 className="trace__id">{goal.id.slice(0, 8)}</h1>
          <p className="trace__sub">
            {agentLabel(goal.agent_type)}{" "}
            <span className="mono">
              {goal.agent_type} {goal.agent_version}
            </span>
            {" · opened "}
            {formatStamp(goal.opened_at)}
            {goal.terminal_outcome ? ` · ${outcomeLabel(goal.terminal_outcome)}` : ""}
          </p>
        </div>
        <StateChip state={goal.state} />
      </header>

      <div className="fingerprint">
        <span className="fingerprint__label">Trigger fingerprint · idempotency key</span>
        <div className="fingerprint__row">
          <code className="fingerprint__value">{goal.trigger_fingerprint}</code>
          <button type="button" className="fingerprint__copy" onClick={copyFingerprint}>
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>

      <section className="panel" aria-label="Goal events">
        {events.length === 0 ? (
          <p className="goals__empty">No events recorded for this goal yet.</p>
        ) : (
          <ol className="tracelog">
            {events.map((event, index) => (
              <TraceEvent
                key={event.sequence}
                event={event}
                terminal={
                  index === events.length - 1 && event.event_type === "outcome_recorded"
                }
              />
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
