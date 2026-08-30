/**
 * The agent catalog: what is actually live, what is specified, and how each
 * one is configured for this tenant.
 *
 * Honesty rule: LIVE means the runtime has shipped and the counters beside it
 * are real reads. Everything else says which increment ships it.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/app/api";
import { useSession } from "@/app/session";
import type { AgentCatalogEntry } from "@/app/types";
import "./Agents.css";

const SHIPS_IN: Record<string, string> = {
  reactive_status_email: "Ships in Increment 3",
  pod_collection: "Ships in Increment 4",
  eta_confirmation: "Ships in Increment 4",
  detention_risk: "Ships in Increment 4",
};

const TRIGGER_LABEL: Record<string, string> = {
  scanner: "Scans the board",
  inbound: "Answers inbound email",
};

/** Operator wording for the known config keys; anything new falls back to mono. */
const CONFIG_LABEL: Record<string, string> = {
  late_threshold_minutes: "Late threshold",
  max_tracking_age_minutes: "Max tracking age",
  schedule: "Send window",
};

function configValue(key: string, value: unknown): string {
  if (key.endsWith("_minutes")) return `${String(value)} min`;
  return String(value);
}

function AgentCard({ agent, tenantName }: { agent: AgentCatalogEntry; tenantName: string }) {
  const configEntries = Object.entries(agent.config);
  return (
    <article className="agentcard" aria-label={agent.display_name}>
      <header className="agentcard__head">
        <div>
          <h2 className="agentcard__name">{agent.display_name}</h2>
          <p className="agentcard__type mono">
            {agent.agent_type} {agent.version} · {agent.trigger_kind}
          </p>
        </div>
        {agent.live ? (
          <span className="agentbadge agentbadge--live">Live</span>
        ) : (
          <span className="agentbadge agentbadge--specified">Specified</span>
        )}
      </header>

      <p className="agentcard__description">{agent.description}</p>

      <div className="agentcard__meta">
        <span className="agentcard__trigger">
          {TRIGGER_LABEL[agent.trigger_kind] ?? agent.trigger_kind}
        </span>
        {!agent.live ? (
          <span className="agentcard__ships">{SHIPS_IN[agent.agent_type] ?? "Specified"}</span>
        ) : null}
      </div>

      <div className={`agentswitch${agent.enabled ? " agentswitch--on" : ""}`}>
        <span className="agentswitch__track" aria-hidden="true">
          <span className="agentswitch__thumb" />
        </span>
        <span className="agentswitch__label">
          {agent.enabled ? "On" : "Off"} for {tenantName}
        </span>
      </div>

      {configEntries.length > 0 ? (
        <dl className="agentconfig">
          {configEntries.map(([key, value]) => (
            <div key={key} className="agentconfig__row">
              <dt>{CONFIG_LABEL[key] ?? <span className="mono">{key}</span>}</dt>
              <dd>{configValue(key, value)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="agentcard__noconfig">No tenant configuration yet.</p>
      )}

      <footer className="agentcard__counts">
        <span>
          <b>{agent.counts.goals_7d}</b> goals · 7 days
        </span>
        <span>
          <b>{agent.counts.succeeded_7d}</b> acted · 7 days
        </span>
      </footer>
    </article>
  );
}

export function AgentsPage() {
  const { activeTenantSlug, session } = useSession();
  // The catalog is always read in one tenant's scope; "all" is not a config view.
  const tenantSlug =
    activeTenantSlug && activeTenantSlug !== "all"
      ? activeTenantSlug
      : (session?.tenants[0]?.slug ?? null);
  const tenantName =
    session?.tenants.find((tenant) => tenant.slug === tenantSlug)?.name ?? tenantSlug ?? "";

  const catalogQuery = useQuery({
    queryKey: ["agent-catalog", tenantSlug],
    queryFn: () => api.agentCatalog(tenantSlug as string),
    enabled: Boolean(tenantSlug),
  });

  if (!tenantSlug) {
    return <p className="agents__empty">Select a tenant to see its agent roster.</p>;
  }

  return (
    <div className="agents">
      <header className="agents__head">
        <div>
          <h1 className="agents__title">Agents</h1>
          <p className="agents__subtitle">
            The roster for {tenantName}: one agent is live, the rest are specified and say
            so.
          </p>
        </div>
      </header>

      {catalogQuery.isPending ? (
        <p className="agents__empty">Reading the agent catalog…</p>
      ) : catalogQuery.isError ? (
        <p className="agents__empty">{(catalogQuery.error as Error).message}</p>
      ) : catalogQuery.data.length === 0 ? (
        <p className="agents__empty">No agents are registered on this platform yet.</p>
      ) : (
        <div className="agents__grid">
          {catalogQuery.data.map((agent) => (
            <AgentCard key={agent.agent_type} agent={agent} tenantName={tenantName} />
          ))}
        </div>
      )}
    </div>
  );
}
