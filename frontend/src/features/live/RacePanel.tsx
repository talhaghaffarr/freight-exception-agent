/**
 * Racing scanners, run on demand.
 *
 * The button starts two real database connections that meet at a barrier and
 * issue the same INSERT. What renders below is what PostgreSQL returned: one
 * insert, one unique violation, one goal. Nothing here is staged.
 */

import { useMutation } from "@tanstack/react-query";

import { api } from "@/app/api";
import type { RaceResult } from "@/app/types";

export function RacePanel({ tenantSlug, reference }: { tenantSlug: string; reference: string }) {
  const race = useMutation({
    mutationFn: () => api.raceScanners(tenantSlug, reference),
  });

  const result: RaceResult | undefined = race.data;

  return (
    <section className="decision" aria-label="Idempotency under concurrent scanners">
      <header className="decision__head">
        <h3 className="decision__title">Idempotency · racing scanners</h3>
        <button
          type="button"
          className="button"
          onClick={() => race.mutate()}
          disabled={race.isPending}
        >
          {race.isPending ? "Racing…" : "Race two scanners"}
        </button>
      </header>

      <div className="racebody">
        <p className="racebody__intro">
          Two connections open the same trigger at once. Enforced by{" "}
          <code>goals_idempotency_key</code>, not by worker state.
        </p>

        {race.isError ? (
          <p className="racebody__error">{(race.error as Error).message}</p>
        ) : null}

        {result ? (
          <>
            <ul className="attempts">
              {result.attempts.map((attempt) => (
                <li
                  key={attempt.worker}
                  className={`attempt attempt--${attempt.created ? "won" : "lost"}`}
                >
                  <span className="attempt__worker">{attempt.worker}</span>
                  <span className="attempt__verdict">
                    {attempt.created ? "INSERT" : "UNIQUE CONFLICT"}
                  </span>
                  <span className="attempt__meta">
                    {attempt.goal_id.slice(0, 8)} · {attempt.duration_ms.toFixed(1)}ms
                  </span>
                </li>
              ))}
            </ul>

            <div className="factgrid">
              <div className="fact">
                <div className="fact__label">Goals created</div>
                <div className="fact__value">{result.goals_created}</div>
              </div>
              <div className="fact">
                <div className="fact__label">Opened events</div>
                <div className="fact__value">{result.opened_events}</div>
              </div>
              <div className="fact">
                <div className="fact__label">Duplicates prevented</div>
                <div className="fact__value">{result.duplicates_prevented}</div>
              </div>
            </div>

            <dl className="evidence">
              <div className="evidence__row">
                <dt>Enforced by</dt>
                <dd>{result.constraint}</dd>
              </div>
              <div className="evidence__row">
                <dt>Trigger fingerprint</dt>
                <dd>{result.trigger_fingerprint}</dd>
              </div>
            </dl>
          </>
        ) : null}
      </div>
    </section>
  );
}
