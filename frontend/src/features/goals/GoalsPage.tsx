/**
 * The goals queue: every episode an agent opened, what it did, or why it
 * declined. The state filter lives in the URL so a filtered view survives a
 * refresh and can be handed to a colleague as a link.
 */

import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "@/app/api";
import { useSession } from "@/app/session";
import type { GoalRow } from "@/app/types";
import {
  STATE_LABEL,
  agentLabel,
  formatStamp,
  outcomeLabel,
  stateTone,
} from "./labels";
import "./Goals.css";

/** Chip order mirrors the goal lifecycle: live work first, history after. */
const STATE_ORDER = [
  "opened",
  "collecting_facts",
  "evaluating",
  "action_pending",
  "executing",
  "waiting",
  "needs_review",
  "succeeded",
  "suppressed",
  "failed",
  "expired",
] as const;

export function StateChip({ state }: { state: string }) {
  return (
    <span className={`goalchip goalchip--${stateTone(state)}`}>
      {STATE_LABEL[state] ?? state}
    </span>
  );
}

function GoalTableRow({ row }: { row: GoalRow }) {
  const navigate = useNavigate();
  return (
    <tr className="goalrow" onClick={() => navigate(`/goals/${row.id}`)}>
      <td className="goalrow__ref">
        <Link to={`/goals/${row.id}`} onClick={(event) => event.stopPropagation()}>
          {row.reference ?? row.id.slice(0, 8)}
        </Link>
      </td>
      <td>
        {agentLabel(row.agent_type)}
        <span className="goalrow__version">{row.agent_version}</span>
      </td>
      <td className="goalrow__subject">{row.subject_label ?? "—"}</td>
      <td>
        <StateChip state={row.state} />
      </td>
      <td className="goalrow__outcome">
        {row.terminal_outcome ? outcomeLabel(row.terminal_outcome) : "—"}
      </td>
      <td className="goalrow__time">{formatStamp(row.opened_at)}</td>
      <td className="goalrow__time">{formatStamp(row.closed_at)}</td>
    </tr>
  );
}

export function GoalsPage() {
  const { activeTenantSlug, session } = useSession();
  // Goals are always read in one tenant's scope; "all" is not a queue view.
  const tenantSlug =
    activeTenantSlug && activeTenantSlug !== "all"
      ? activeTenantSlug
      : (session?.tenants[0]?.slug ?? null);

  const [searchParams, setSearchParams] = useSearchParams();
  const stateFilter = searchParams.get("state");

  const goalsQuery = useQuery({
    queryKey: ["goals", tenantSlug, stateFilter],
    queryFn: () => api.listGoals(tenantSlug as string, { state: stateFilter }),
    enabled: Boolean(tenantSlug),
  });

  if (!tenantSlug) {
    return <p className="goals__empty">Select a tenant to see its goal queue.</p>;
  }

  const rows = goalsQuery.data?.rows ?? [];
  const counts = goalsQuery.data?.counts ?? {};
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);

  const setFilter = (state: string | null) => {
    if (state === null) {
      setSearchParams({}, { replace: true });
    } else {
      setSearchParams({ state }, { replace: true });
    }
  };

  return (
    <div className="goals">
      <header className="goals__head">
        <div>
          <h1 className="goals__title">Goals</h1>
          <p className="goals__subtitle">
            Every job an agent picked up — what it did, or exactly why it declined.
          </p>
        </div>
      </header>

      <nav className="statefilter" aria-label="Filter goals by state">
        <button
          type="button"
          className="statefilter__chip"
          aria-pressed={stateFilter === null}
          onClick={() => setFilter(null)}
        >
          All{" "}
          <span className="statefilter__count">{total}</span>
        </button>
        {STATE_ORDER.filter((state) => (counts[state] ?? 0) > 0).map((state) => (
          <button
            key={state}
            type="button"
            className={`statefilter__chip statefilter__chip--${stateTone(state)}`}
            aria-pressed={stateFilter === state}
            onClick={() => setFilter(state)}
          >
            {STATE_LABEL[state]}{" "}
            <span className="statefilter__count">{counts[state]}</span>
          </button>
        ))}
      </nav>

      <section className="panel" aria-label="Goal queue">
        {goalsQuery.isPending ? (
          <p className="goals__empty">Reading the goal ledger…</p>
        ) : goalsQuery.isError ? (
          <p className="goals__empty">{(goalsQuery.error as Error).message}</p>
        ) : rows.length === 0 ? (
          <p className="goals__empty">
            {stateFilter
              ? `No goals in “${STATE_LABEL[stateFilter] ?? stateFilter}” right now.`
              : "No agent has opened a goal for this tenant yet."}
          </p>
        ) : (
          <table className="goaltable">
            <thead>
              <tr>
                <th scope="col">Ref</th>
                <th scope="col">Agent</th>
                <th scope="col">Stop</th>
                <th scope="col">State</th>
                <th scope="col">Outcome</th>
                <th scope="col">Opened</th>
                <th scope="col">Closed</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <GoalTableRow key={row.id} row={row} />
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
