import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { AgentCatalogEntry } from "@/app/types";
import { AgentsPage } from "@/features/agents/AgentsPage";
import { renderWithProviders } from "@/test/render";

function entry(overrides: Partial<AgentCatalogEntry> = {}): AgentCatalogEntry {
  return {
    agent_type: "late_pickup",
    version: "1.0.0",
    trigger_kind: "scanner",
    display_name: "Late Pickup Alert",
    description: "Scans active loads and alerts the account manager.",
    live: true,
    enabled: true,
    config: {
      late_threshold_minutes: 30,
      max_tracking_age_minutes: 30,
      schedule: "06:00-22:00 America/Chicago",
    },
    counts: { goals_7d: 44, succeeded_7d: 14 },
    ...overrides,
  };
}

const CATALOG: AgentCatalogEntry[] = [
  entry(),
  entry({
    agent_type: "reactive_status_email",
    version: "0.1.0",
    trigger_kind: "inbound",
    display_name: "Reactive Status Email",
    description: "Answers a verified customer's status email.",
    live: false,
    enabled: false,
    config: {},
    counts: { goals_7d: 0, succeeded_7d: 0 },
  }),
  entry({
    agent_type: "pod_collection",
    version: "0.1.0",
    display_name: "POD Collection",
    description: "Chases the proof-of-delivery document.",
    live: false,
    enabled: false,
    config: {},
    counts: { goals_7d: 0, succeeded_7d: 0 },
  }),
];

describe("AgentsPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "agentCatalog").mockResolvedValue(CATALOG);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("marks the shipped agent LIVE and the rest SPECIFIED", async () => {
    renderWithProviders(<AgentsPage />);

    const late = await screen.findByRole("article", { name: /late pickup alert/i });
    expect(within(late).getByText("Live")).toBeVisible();

    const reactive = screen.getByRole("article", { name: /reactive status email/i });
    expect(within(reactive).getByText("Specified")).toBeVisible();
    expect(within(reactive).getByText(/ships in increment 3/i)).toBeVisible();

    const pod = screen.getByRole("article", { name: /pod collection/i });
    expect(within(pod).getByText(/ships in increment 4/i)).toBeVisible();
  });

  it("shows the tenant's own enabled state, read-only", async () => {
    renderWithProviders(<AgentsPage />);

    const late = await screen.findByRole("article", { name: /late pickup alert/i });
    expect(within(late).getByText(/on for atlas brokerage/i)).toBeVisible();
    // A read-only state display, not a control.
    expect(within(late).queryByRole("switch")).not.toBeInTheDocument();

    const reactive = screen.getByRole("article", { name: /reactive status email/i });
    expect(within(reactive).getByText(/off for atlas brokerage/i)).toBeVisible();
  });

  it("renders config in operator language with real units", async () => {
    renderWithProviders(<AgentsPage />);

    const late = await screen.findByRole("article", { name: /late pickup alert/i });
    expect(within(late).getByText("Late threshold")).toBeVisible();
    expect(within(late).getAllByText("30 min")).toHaveLength(2);
    expect(within(late).getByText("06:00-22:00 America/Chicago")).toBeVisible();
  });

  it("shows real seven-day counters per agent", async () => {
    renderWithProviders(<AgentsPage />);

    const late = await screen.findByRole("article", { name: /late pickup alert/i });
    expect(within(late).getByText("44")).toBeVisible();
    expect(within(late).getByText("14")).toBeVisible();
  });
});
