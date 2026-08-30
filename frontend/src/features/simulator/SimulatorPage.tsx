/**
 * Scenario simulator — live.
 *
 * The two wired cards call the same endpoints the console uses; every run
 * hits the real database and renders whatever PostgreSQL returned. The
 * remaining scenarios are specified and say which increment ships them.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/app/api";
import { useSession } from "@/app/session";
import type { RaceResult } from "@/app/types";
import "./Simulator.css";

const RACE_REFERENCE = "LD-1048";

const SPECIFIED_SCENARIOS = [
  {
    id: "late-pickup",
    title: "Late pickup end-to-end",
    description: "Run one scan and watch a late load become a sent alert, end to end.",
    arrival: "Arrives with the worker dispatch path (Increment 2).",
  },
  {
    id: "stale-gps",
    title: "Stale-GPS honest unknown",
    description: "Age out tracking and watch the ETA become a named unknown, not a guess.",
    arrival: "Arrives with the worker dispatch path (Increment 2).",
  },
  {
    id: "inbound-email",
    title: "Inbound status email",
    description: "Send a customer status email through every safety gate to a computed reply.",
    arrival: "Arrives with Reactive Email (Increment 3).",
  },
];

function RaceResultView({ result }: { result: RaceResult }) {
  return (
    <>
      <ul className="sim-attempts">
        {result.attempts.map((attempt) => (
          <li
            key={attempt.worker}
            className={`sim-attempt sim-attempt--${attempt.created ? "won" : "lost"}`}
          >
            <span className="sim-attempt__worker">{attempt.worker}</span>
            <span className="sim-attempt__verdict">
              {attempt.created ? "INSERT" : "UNIQUE CONFLICT"}
            </span>
            <span className="sim-attempt__meta">
              {attempt.goal_id.slice(0, 8)} · {attempt.duration_ms.toFixed(1)}ms
            </span>
          </li>
        ))}
      </ul>

      <div className="sim-facts">
        <div className="sim-fact">
          <div className="sim-fact__label">Goals created</div>
          <div className="sim-fact__value">{result.goals_created}</div>
        </div>
        <div className="sim-fact">
          <div className="sim-fact__label">Opened events</div>
          <div className="sim-fact__value">{result.opened_events}</div>
        </div>
        <div className="sim-fact">
          <div className="sim-fact__label">Duplicates prevented</div>
          <div className="sim-fact__value">{result.duplicates_prevented}</div>
        </div>
      </div>

      <dl className="sim-evidence">
        <div className="sim-evidence__row">
          <dt>Enforced by</dt>
          <dd>{result.constraint}</dd>
        </div>
        <div className="sim-evidence__row">
          <dt>Trigger fingerprint</dt>
          <dd>{result.trigger_fingerprint}</dd>
        </div>
      </dl>
    </>
  );
}

export function SimulatorPage() {
  const { activeTenantSlug, session } = useSession();
  // A scenario always runs in one tenant's scope; "all" is not a run target.
  const tenantSlug =
    activeTenantSlug && activeTenantSlug !== "all"
      ? activeTenantSlug
      : (session?.tenants[0]?.slug ?? null);

  const queryClient = useQueryClient();

  const race = useMutation({
    mutationFn: () => api.raceScanners(tenantSlug as string, RACE_REFERENCE),
  });

  const reset = useMutation({
    mutationFn: () => api.resetDemo(tenantSlug as string),
    // Reset moves appointments; anything the console cached is now stale.
    onSuccess: () => queryClient.invalidateQueries(),
  });

  if (!tenantSlug) {
    return <p className="sim__empty">Select a tenant to run scenarios.</p>;
  }

  return (
    <div className="sim">
      <header className="sim__head">
        <div>
          <h1 className="sim__title">Scenario simulator</h1>
          <p className="sim__subtitle">
            Prove the failure modes on demand — every run hits the real database.
          </p>
        </div>
        <span className="sim__tenant">tenant {tenantSlug}</span>
      </header>

      <div className="sim__grid">
        <section className="sim-card sim-card--wide" aria-label="Racing scanners">
          <header className="sim-card__head">
            <h2 className="sim-card__title">Racing scanners</h2>
            <span className="sim-chip sim-chip--live">Live</span>
          </header>
          <div className="sim-card__body">
            <p className="sim-card__desc">
              Two scanners try to create the same alert at once. The database lets exactly
              one through.
            </p>
            <p className="sim-card__target">
              under the hood: two connections, one INSERT each, same trigger — the unique
              constraint <code>goals_idempotency_key</code> decides · target{" "}
              <code>{RACE_REFERENCE}</code>
            </p>
            <div className="sim-card__actions">
              <button
                type="button"
                className="sim-button"
                onClick={() => race.mutate()}
                disabled={race.isPending}
              >
                {race.isPending ? "Racing…" : "Race two scanners"}
              </button>
            </div>
            {race.isError ? (
              <p className="sim-error">{(race.error as Error).message}</p>
            ) : null}
            {race.data ? <RaceResultView result={race.data} /> : null}
          </div>
        </section>

        <section className="sim-card" aria-label="Reset demo">
          <header className="sim-card__head">
            <h2 className="sim-card__title">Reset demo</h2>
            <span className="sim-chip sim-chip--live">Live</span>
          </header>
          <div className="sim-card__body">
            <p className="sim-card__desc">
              Re-anchor appointments to now and clear demo goals.
            </p>
            <div className="sim-card__actions">
              <button
                type="button"
                className="sim-button"
                onClick={() => reset.mutate()}
                disabled={reset.isPending}
              >
                {reset.isPending ? "Resetting…" : "Reset demo"}
              </button>
            </div>
            {reset.isError ? (
              <p className="sim-error">{(reset.error as Error).message}</p>
            ) : null}
            {reset.data ? (
              <div className="sim-facts">
                <div className="sim-fact">
                  <div className="sim-fact__label">Goals cleared</div>
                  <div className="sim-fact__value">{reset.data.goals_cleared}</div>
                </div>
                <div className="sim-fact">
                  <div className="sim-fact__label">Loads reseeded</div>
                  <div className="sim-fact__value">{reset.data.loads_reseeded}</div>
                </div>
              </div>
            ) : null}
          </div>
        </section>

        {SPECIFIED_SCENARIOS.map((scenario) => (
          <section key={scenario.id} className="sim-card" aria-label={scenario.title}>
            <header className="sim-card__head">
              <h2 className="sim-card__title">{scenario.title}</h2>
              <span className="sim-chip sim-chip--specified">Specified</span>
            </header>
            <div className="sim-card__body">
              <p className="sim-card__desc">{scenario.description}</p>
              <p className="sim-card__arrival">{scenario.arrival}</p>
              <div className="sim-card__actions">
                <button type="button" className="sim-button" disabled title="Design preview">
                  Run scenario
                </button>
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
