/**
 * System Health.
 *
 * Readiness and status are shown separately because they answer different
 * questions: "is anything impaired?" and "should this instance take traffic?".
 * A degraded optional provider is the normal case where those two diverge.
 */

import type { ComponentHealth, HealthReport } from "@/app/types";
import { StatusBadge } from "@/components/StatusBadge";

import "@/styles/page.css";

const COMPONENT_LABELS: Record<string, string> = {
  api: "API",
  database: "PostgreSQL",
  migrations: "Migrations",
  valkey: "Valkey",
  worker: "Celery workers",
  beat: "Celery Beat",
  email: "Email (Mailpit)",
  sms: "SMS simulator",
  voice: "Voice simulator",
};

function label(component: ComponentHealth): string {
  return COMPONENT_LABELS[component.name] ?? component.name;
}

function formatMetadata(metadata: Record<string, unknown>): string | null {
  const entries = Object.entries(metadata);
  if (entries.length === 0) return null;
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(" · ");
}

export interface SystemHealthPageProps {
  health?: HealthReport;
  isLoading?: boolean;
  error?: string | null;
}

export function SystemHealthPage({ health, isLoading = false, error = null }: SystemHealthPageProps) {
  if (error) {
    return (
      <section className="page" aria-labelledby="system-heading">
        <header className="page__header">
          <h1 id="system-heading" className="page__title">
            System Health
          </h1>
        </header>
        <div className="callout" data-tone="critical" role="alert">
          <span>The health endpoint could not be reached: {error}</span>
        </div>
      </section>
    );
  }

  if (isLoading || !health) {
    return (
      <section className="page" aria-labelledby="system-heading" aria-busy="true">
        <header className="page__header">
          <h1 id="system-heading" className="page__title">
            System Health
          </h1>
        </header>
        <div className="skeleton" data-testid="system-skeleton">
          <div className="skeleton__block" />
        </div>
      </section>
    );
  }

  const notReady = health.components.filter(
    (component) => component.required && component.status !== "healthy",
  );

  return (
    <section className="page" aria-labelledby="system-heading">
      <header className="page__header">
        <div>
          <h1 id="system-heading" className="page__title">
            System Health
          </h1>
          <p className="page__subtitle">
            Last checked <time dateTime={health.checked_at}>{health.checked_at}</time>
          </p>
        </div>
        <StatusBadge status={health.status} />
      </header>

      <div
        className="callout"
        data-tone={health.ready ? "positive" : "critical"}
        data-testid="readiness"
      >
        <span>
          {health.ready
            ? "Ready to serve traffic. A degraded optional provider does not remove this instance from rotation."
            : `Not ready to serve traffic: ${notReady.map(label).join(", ")} cannot prove it is healthy.`}
        </span>
      </div>

      <section className="panel" aria-labelledby="components-heading">
        <div className="panel__head">
          <h2 id="components-heading" className="panel__title">
            Components
          </h2>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <caption>
              Required components gate readiness. Optional components degrade the platform without
              taking it out of rotation.
            </caption>
            <thead>
              <tr>
                <th scope="col">Component</th>
                <th scope="col">Status</th>
                <th scope="col">Role</th>
                <th scope="col" className="numeric">
                  Latency
                </th>
                <th scope="col">Last check</th>
                <th scope="col">Detail</th>
              </tr>
            </thead>
            <tbody>
              {health.components.map((component) => (
                <tr key={component.name}>
                  <th scope="row">
                    {label(component)}{" "}
                    {/* The wire name is what appears in logs and in the health
                        payload; showing both is how an operator correlates. */}
                    <code className="muted">{component.name}</code>
                  </th>
                  <td>
                    <StatusBadge status={component.status} size="sm" />
                  </td>
                  <td>{component.required ? "Required" : "Optional"}</td>
                  <td className="numeric">{component.latency_ms.toFixed(1)} ms</td>
                  <td>
                    <time dateTime={component.checked_at}>{component.checked_at}</time>
                  </td>
                  <td className="muted">
                    {component.detail ?? formatMetadata(component.metadata) ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
