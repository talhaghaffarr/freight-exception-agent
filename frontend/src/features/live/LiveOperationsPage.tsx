/**
 * Live load control.
 *
 * The board ranks by operational urgency rather than by lateness alone: a load
 * whose ETA cannot be computed outranks one that is merely a few minutes
 * behind, because an unknown needs a human and a small delay usually does not.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/app/api";
import { useSession } from "@/app/session";
import type { BoardRow } from "@/app/types";
import { AgentDecision } from "./AgentDecision";
import { LoadMap } from "./LoadMap";
import { RacePanel } from "./RacePanel";
import {
  CLASSIFICATION_LABEL,
  FRESHNESS_LABEL,
  formatAge,
  formatClock,
  formatLateness,
  rowBadge,
  shortReason,
} from "./facts";
import "./LiveOperations.css";

const BOARD_POLL_MS = 20_000;

function LoadRow({
  row,
  selected,
  onSelect,
}: {
  row: BoardRow;
  selected: boolean;
  onSelect: (reference: string) => void;
}) {
  return (
    <li className="loadlist__item">
      <button
        type="button"
        className="loadlist__button"
        aria-current={selected}
        onClick={() => onSelect(row.reference)}
      >
        <span className="loadlist__top">
          <span className="loadlist__ref">{row.reference}</span>
          <span className={`chip chip--${row.facts.classification}`}>{rowBadge(row)}</span>
        </span>
        <p className="loadlist__lane">
          {row.origin} → {row.destination}
        </p>
        <p className="loadlist__meta">
          <span>Pickup {formatClock(row.pickup_appointment)}</span>
          <span>GPS {formatAge(row.facts.evidence_at)}</span>
          {row.carrier_name ? <span>{row.carrier_name}</span> : null}
        </p>
      </button>
    </li>
  );
}

export function LiveOperationsPage() {
  const { activeTenantSlug, session } = useSession();
  // The board is always read in one tenant's scope; "all" is not a board view.
  const tenantSlug =
    activeTenantSlug && activeTenantSlug !== "all"
      ? activeTenantSlug
      : (session?.tenants[0]?.slug ?? null);

  const [selected, setSelected] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Appointments are absolute, so a board left open drifts away from the
  // figures the walkthrough describes. Reset re-anchors it to now.
  const resetDemo = useMutation({
    mutationFn: () => api.resetDemo(tenantSlug as string),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const boardQuery = useQuery({
    queryKey: ["board", tenantSlug],
    queryFn: () => api.loads(tenantSlug as string),
    enabled: Boolean(tenantSlug),
    refetchInterval: BOARD_POLL_MS,
  });

  const reference = selected ?? boardQuery.data?.rows[0]?.reference ?? null;

  const loadQuery = useQuery({
    queryKey: ["load", tenantSlug, reference],
    queryFn: () => api.load(tenantSlug as string, reference as string),
    enabled: Boolean(tenantSlug && reference),
  });

  if (!tenantSlug) {
    return <p className="live__empty">Select a tenant to see its load board.</p>;
  }

  const summary = boardQuery.data?.summary;
  const load = loadQuery.data;

  return (
    <div className="live">
      <header className="live__head">
        <div>
          <h1 className="live__title">Live load control</h1>
          <p className="live__subtitle">
            {summary ? `${summary.active_loads} active truckloads` : "Loading…"}
            {boardQuery.data?.generatedAt
              ? ` · updated ${formatAge(boardQuery.data.generatedAt)}`
              : ""}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <span className="live__sandbox">
            Sandbox · synthetic data · no external sends
          </span>
          <button
            type="button"
            className="button button--quiet"
            onClick={() => resetDemo.mutate()}
            disabled={resetDemo.isPending}
          >
            {resetDemo.isPending ? "Resetting…" : "Reset demo"}
          </button>
        </div>
      </header>

      {summary ? (
        <div className="counters">
          <div className="counter counter--flag">
            <span className="counter__value">{summary.needs_action}</span>
            <span className="counter__label">
              Needs action
              <span className="counter__note">Prioritized</span>
            </span>
          </div>
          <div className="counter">
            <span className="counter__value">{summary.late_pickup}</span>
            <span className="counter__label">
              Late pickup
              <span className="counter__note">ETA at risk</span>
            </span>
          </div>
          <div className="counter">
            <span className="counter__value">{summary.at_risk}</span>
            <span className="counter__label">
              At risk
              <span className="counter__note">Under threshold</span>
            </span>
          </div>
          <div className="counter">
            <span className="counter__value">{summary.no_signal}</span>
            <span className="counter__label">
              No signal
              <span className="counter__note">Tracking stale</span>
            </span>
          </div>
          <div className="counter">
            <span className="counter__value">{summary.on_track}</span>
            <span className="counter__label">
              On track
              <span className="counter__note">No action</span>
            </span>
          </div>
          <div className="counter">
            <span className="counter__value">{summary.not_started}</span>
            <span className="counter__label">
              Not started
              <span className="counter__note">Pre-pickup</span>
            </span>
          </div>
        </div>
      ) : null}

      <div className="live__split">
        <section className="panel panel--list" aria-label="Priority loads">
          <header className="panel__head">
            <h2 className="panel__title">Priority loads</h2>
            <span className="check__detail">Risk ↓</span>
          </header>
          {boardQuery.isPending ? (
            <p className="live__empty">Loading loads…</p>
          ) : boardQuery.isError ? (
            <p className="live__empty">{(boardQuery.error as Error).message}</p>
          ) : (
            <ul className="loadlist">
              {boardQuery.data?.rows.map((row) => (
                <LoadRow
                  key={row.load_id}
                  row={row}
                  selected={row.reference === reference}
                  onSelect={setSelected}
                />
              ))}
            </ul>
          )}
        </section>

        <section className="panel panel--map" aria-label="Load positions">
          <header className="panel__head">
            <h2 className="panel__title">Positions</h2>
            <span className="check__detail">OpenFreeMap · MapLibre</span>
          </header>
          <LoadMap
            rows={boardQuery.data?.rows ?? []}
            selected={boardQuery.data?.rows.find((row) => row.reference === reference) ?? null}
            onSelect={setSelected}
          />
        </section>

        <section className="panel panel--detail" aria-label="Selected load">
          {load ? (
            <div className="detail__body">
              <div className="detail__lede">
                <div>
                  <h2 className="detail__ref">{load.reference}</h2>
                  <p className="detail__sub">
                    {load.customer_name} · {load.carrier_name ?? "no carrier"} ·{" "}
                    {load.driver_name ?? "no driver"}
                  </p>
                  <p className="detail__sub">
                    {load.origin} → {load.destination}
                  </p>
                </div>
                <span className={`chip chip--${load.facts.classification}`}>
                  {CLASSIFICATION_LABEL[load.facts.classification]}
                </span>
              </div>

              <div className="factgrid">
                <div className="fact">
                  <div className="fact__label">Pickup appointment</div>
                  <div className="fact__value">{formatClock(load.facts.appointment_start)}</div>
                  <div className="fact__note">{`rev ${load.facts.appointment_revision ?? "—"}`}</div>
                </div>
                <div className="fact">
                  <div className="fact__label">Computed ETA</div>
                  {load.facts.eta.available ? (
                    <>
                      <div className="fact__value">
                        {formatClock(load.facts.eta.predicted_arrival)}
                      </div>
                      <div className="fact__note">{load.facts.eta.traffic_assumption}</div>
                    </>
                  ) : (
                    <>
                      <div className="fact__value fact__value--unknown">Unknown</div>
                      <div className="fact__note">{shortReason(load.facts)}</div>
                    </>
                  )}
                </div>
                <div className="fact">
                  <div className="fact__label">Risk</div>
                  <div
                    className={`fact__value${
                      load.facts.minutes_late === null ? " fact__value--unknown" : ""
                    }`}
                  >
                    {formatLateness(load.facts)}
                  </div>
                  <div className="fact__note">{`threshold ${load.facts.threshold_minutes}m`}</div>
                </div>
                <div className="fact">
                  <div className="fact__label">Tracking</div>
                  <div className="fact__value fact__value--unknown">
                    {load.facts.tracking_freshness
                      ? FRESHNESS_LABEL[load.facts.tracking_freshness]
                      : "No signal"}
                  </div>
                  <div className="fact__note">{formatAge(load.facts.evidence_at)}</div>
                </div>
              </div>

              <AgentDecision load={load} />

              <RacePanel tenantSlug={tenantSlug} reference={load.reference} />

              <dl className="evidence">
                <div className="evidence__row">
                  <dt>Account manager</dt>
                  <dd>{load.account_manager.email}</dd>
                </div>
                <div className="evidence__row">
                  <dt>Latest position</dt>
                  <dd>
                    {load.facts.position
                      ? `${load.facts.position.latitude.toFixed(4)}, ${load.facts.position.longitude.toFixed(4)}`
                      : "none reported"}
                  </dd>
                </div>
                <div className="evidence__row">
                  <dt>Evidence timestamp</dt>
                  <dd>{load.facts.evidence_at ?? "none"}</dd>
                </div>
                <div className="evidence__row">
                  <dt>Open goals</dt>
                  <dd>
                    {load.goals.length === 0
                      ? "none"
                      : load.goals.map((goal) => `${goal.state} (${goal.id.slice(0, 8)})`).join(", ")}
                  </dd>
                </div>
              </dl>

              <p className="notimpl">
                Not in this build · notification rendering, provider delivery and outcome
                recording. The decision above stops at goal creation.
              </p>
            </div>
          ) : (
            <p className="live__empty">
              {loadQuery.isError
                ? (loadQuery.error as Error).message
                : "Select a load to see its facts and the agent's decision."}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
