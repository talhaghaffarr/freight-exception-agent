/**
 * Fleet Overview.
 *
 * The home screen answers one question: is the agent fleet healthy and is it
 * producing value? Before any agent has run it says so plainly rather than
 * showing plausible-looking zeros dressed up as results.
 */

import { Link } from "react-router-dom";

import type { Dashboard } from "@/app/types";
import { StatusBadge } from "@/components/StatusBadge";

import "@/styles/page.css";

function humanizeAgentType(agentType: string): string {
  return agentType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function Metric({
  label,
  value,
  hint,
  testId,
}: {
  label: string;
  value: string | number;
  hint?: string;
  testId?: string;
}) {
  return (
    <div className="metric" data-testid={testId}>
      <span className="metric__label">{label}</span>
      <span className="metric__value">{value}</span>
      {hint && <span className="metric__hint">{hint}</span>}
    </div>
  );
}

export interface OverviewPageProps {
  dashboard?: Dashboard;
  isLoading?: boolean;
}

export function OverviewPage({ dashboard, isLoading = false }: OverviewPageProps) {
  if (isLoading || !dashboard) {
    return (
      <section className="page" aria-labelledby="overview-heading" aria-busy="true">
        <header className="page__header">
          <h1 id="overview-heading" className="page__title">
            Fleet Overview
          </h1>
        </header>
        <div className="skeleton" data-testid="overview-skeleton">
          <div className="skeleton__block" />
          <div className="skeleton__block" />
        </div>
      </section>
    );
  }

  const { goals, communications, value, agents, recent_activity: recentActivity } = dashboard;
  const fleetHasRun = agents.length > 0 || goals.opened > 0;

  return (
    <section className="page" aria-labelledby="overview-heading">
      <header className="page__header">
        <div>
          <h1 id="overview-heading" className="page__title">
            Fleet Overview
          </h1>
          <p className="page__subtitle">
            What the agents did, what they declined to do, and what it was worth.
          </p>
        </div>
      </header>

      <div className="metric-grid" data-testid="goals-summary">
        <Metric label="Goals opened" value={goals.opened} testId="goals-opened" />
        <Metric label="Waiting" value={goals.waiting} testId="goals-waiting" />
        <Metric label="Needs review" value={goals.needs_review} testId="goals-needs_review" />
        <Metric label="Failed" value={goals.failed} testId="goals-failed" />
        <Metric
          label="Operator minutes saved"
          value={value.operator_minutes_saved}
          hint="Manual touches avoided, counted from completed goals"
        />
      </div>

      <div className="metric-grid" data-testid="communications-summary">
        <Metric label="Email sent" value={communications.email} />
        <Metric label="SMS sent" value={communications.sms} />
        <Metric label="Voice calls" value={communications.voice} />
      </div>

      <section className="panel" aria-labelledby="agents-heading">
        <div className="panel__head">
          <h2 id="agents-heading" className="panel__title">
            Agents
          </h2>
        </div>
        {agents.length === 0 ? (
          <div className="panel--empty">
            <p className="panel__lead">No agent has run yet.</p>
            <p className="panel__meta">
              Seeded loads exist, but nothing has triggered. <Link to="/simulator">Open the
              simulator</Link> to run a scenario, or wait for the next scanner interval.
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <caption>Enrolled agents by tenant, with open work and success rate.</caption>
              <thead>
                <tr>
                  <th scope="col">Agent</th>
                  <th scope="col">Tenant</th>
                  <th scope="col">Version</th>
                  <th scope="col">State</th>
                  <th scope="col" className="numeric">
                    Open goals
                  </th>
                  <th scope="col" className="numeric">
                    Success rate
                  </th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr key={`${agent.tenant_slug}:${agent.agent_type}`}>
                    <th scope="row">{humanizeAgentType(agent.agent_type)}</th>
                    <td>{agent.tenant_slug}</td>
                    <td className="mono">{agent.version}</td>
                    <td>
                      <StatusBadge
                        status={agent.enabled ? "healthy" : "suppressed"}
                        label={agent.enabled ? "Enabled" : "Paused"}
                        size="sm"
                      />
                    </td>
                    <td className="numeric">{agent.goals_open}</td>
                    <td className="numeric">
                      {agent.success_rate === null
                        ? "—"
                        : `${Math.round(agent.success_rate * 100)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel" aria-labelledby="activity-heading">
        <div className="panel__head">
          <h2 id="activity-heading" className="panel__title">
            Recent activity
          </h2>
        </div>
        {recentActivity.length === 0 ? (
          <div className="panel--empty">
            <p className="panel__meta">
              {fleetHasRun
                ? "No activity in the selected window."
                : "Activity appears here as soon as a goal opens."}
            </p>
          </div>
        ) : (
          <ul className="panel__body">
            {recentActivity.map((entry) => (
              <li key={entry.id}>
                <time dateTime={entry.occurred_at}>{entry.occurred_at}</time> {entry.summary}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
