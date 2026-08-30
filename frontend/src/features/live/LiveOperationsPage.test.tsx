import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { BoardResponse, LoadDetail } from "@/app/types";
import { LiveOperationsPage } from "@/features/live/LiveOperationsPage";
import { renderWithProviders } from "@/test/render";

function facts(overrides: Partial<LoadDetail["facts"]> = {}): LoadDetail["facts"] {
  return {
    classification: "late",
    minutes_late: 38,
    threshold_minutes: 30,
    reason: null,
    appointment_start: "2026-08-30T15:00:00+00:00",
    appointment_revision: 3,
    tracking_freshness: "fresh",
    evidence_at: "2026-08-30T14:41:00+00:00",
    position: { latitude: 37.2153, longitude: -93.2982 },
    eta: {
      available: true,
      predicted_arrival: "2026-08-30T15:38:00+00:00",
      reason: null,
      source: "route_estimate",
      traffic_assumption: "historical_average",
      remaining_meters: 218900,
    },
    ...overrides,
  };
}

const DARK_FACTS = facts({
  classification: "unknown",
  minutes_late: null,
  reason: "tracking_stale",
  tracking_freshness: "stale",
  eta: {
    available: false,
    predicted_arrival: null,
    reason: "tracking_stale",
    source: null,
    traffic_assumption: null,
    remaining_meters: null,
  },
});

const BOARD: BoardResponse = {
  rows: [
    {
      load_id: "aaaaaaaa-1111-5111-8111-111111111111",
      reference: "LD-1048",
      customer_name: "ACME Retail",
      carrier_name: "BlueLine Logistics",
      driver_name: "R. Okafor",
      origin: "Chicago, IL",
      destination: "Dallas, TX",
      pickup_appointment: "2026-08-30T15:00:00+00:00",
      origin_point: { latitude: 41.8781, longitude: -87.6298 },
      destination_point: { latitude: 32.7767, longitude: -96.797 },
      facts: facts(),
    },
    {
      load_id: "bbbbbbbb-2222-5222-8222-222222222222",
      reference: "LD-1051",
      customer_name: "Northwind Foods",
      carrier_name: "NorthStar Carriers",
      driver_name: "J. Alvarez",
      origin: "Detroit, MI",
      destination: "Nashville, TN",
      pickup_appointment: "2026-08-30T15:30:00+00:00",
      origin_point: { latitude: 42.3314, longitude: -83.0458 },
      destination_point: { latitude: 36.1627, longitude: -86.7816 },
      facts: DARK_FACTS,
    },
  ],
  summary: {
    active_loads: 48,
    needs_action: 6,
    late_pickup: 2,
    at_risk: 1,
    no_signal: 4,
    on_track: 6,
    not_started: 35,
  },
  generatedAt: "2026-08-30T14:43:00+00:00",
};

const DETAIL: LoadDetail = {
  ...BOARD.rows[0]!,
  account_manager: { name: "Dana Reyes", email: "dana.reyes@atlasbrokerage.demo" },
  pickup_facility: "ACME Distribution Center",
  goals: [],
};

describe("LiveOperationsPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "loads").mockResolvedValue(BOARD);
    vi.spyOn(api, "load").mockResolvedValue(DETAIL);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the computed lateness against the configured threshold", async () => {
    renderWithProviders(<LiveOperationsPage />);

    // "+38 min" also appears as the list badge, so assert inside the detail.
    const detail = await screen.findByRole("region", { name: /selected load/i });
    expect(await within(detail).findByText("+38 min")).toBeVisible();
    expect(within(detail).getByText(/threshold 30m/i)).toBeVisible();
  });

  it("renders an unavailable ETA as a named unknown, never as a blank", async () => {
    vi.spyOn(api, "load").mockResolvedValue({ ...DETAIL, facts: DARK_FACTS });
    renderWithProviders(<LiveOperationsPage />);

    const detail = await screen.findByRole("region", { name: /selected load/i });
    await waitFor(() => expect(within(detail).getByText(/^Unknown$/)).toBeVisible());
    expect(within(detail).getAllByText(/tracking stale/i).length).toBeGreaterThan(0);
  });

  it("holds the agent when a required fact is missing and says which", async () => {
    vi.spyOn(api, "load").mockResolvedValue({ ...DETAIL, facts: DARK_FACTS });
    renderWithProviders(<LiveOperationsPage />);

    const decision = await screen.findByRole("region", { name: /agent decision/i });
    expect(within(decision).getByText("Held")).toBeVisible();
    expect(within(decision).getByText(/suppressed/i)).toBeVisible();
  });

  it("declares that notification delivery is not implemented in this build", async () => {
    renderWithProviders(<LiveOperationsPage />);

    expect(
      await screen.findByText(/not in this build/i),
    ).toBeVisible();
  });

  it("labels the environment as a sandbox that sends nothing externally", async () => {
    renderWithProviders(<LiveOperationsPage />);

    expect(await screen.findByText(/no external sends/i)).toBeVisible();
  });

  it("offers the racing-scanner demonstration for the selected load", async () => {
    renderWithProviders(<LiveOperationsPage />);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /race two scanners/i }),
      ).toBeEnabled(),
    );
  });
});
