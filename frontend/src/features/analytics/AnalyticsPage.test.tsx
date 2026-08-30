import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { OutcomeAnalytics } from "@/app/types";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { renderWithProviders } from "@/test/render";

const ANALYTICS: OutcomeAnalytics = {
  outcomes: [
    { outcome: "acted_successfully", count: 14 },
    { outcome: "below_threshold", count: 8 },
    { outcome: "tracking_stale", count: 6 },
  ],
  daily: [
    { date: "2026-08-29", opened: 6, succeeded: 2, suppressed: 3 },
    { date: "2026-08-30", opened: 9, succeeded: 3, suppressed: 5 },
  ],
  value: { operator_minutes_saved: 56 },
};

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "outcomeAnalytics").mockResolvedValue(ANALYTICS);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders one outcome bar per reason, human label first, enum as evidence", async () => {
    renderWithProviders(<AnalyticsPage />);

    const outcomes = await screen.findByRole("region", { name: /outcomes/i });
    expect(
      within(outcomes).getByText(/every reason an agent did or did not act/i),
    ).toBeVisible();
    // Human label and the raw enum both render (chart and its table twin);
    // the enum is secondary evidence, never the primary label.
    expect(within(outcomes).getAllByText("Acted successfully").length).toBeGreaterThan(0);
    expect(within(outcomes).getAllByText("acted_successfully").length).toBeGreaterThan(0);
    expect(within(outcomes).getAllByText("Below threshold").length).toBeGreaterThan(0);
    expect(within(outcomes).getAllByText("Tracking stale").length).toBeGreaterThan(0);
  });

  it("keeps every chart value reachable through a table twin", async () => {
    renderWithProviders(<AnalyticsPage />);

    const outcomes = await screen.findByRole("region", { name: /outcomes/i });
    const table = within(outcomes).getByRole("table", {
      name: /goal outcomes over the last 7 days/i,
    });
    expect(within(table).getByRole("row", { name: /acted successfully 14/i }))
      .toBeInTheDocument();
  });

  it("shows the value tile with its honest footnote", async () => {
    renderWithProviders(<AnalyticsPage />);

    expect(await screen.findByText("Operator minutes saved")).toBeVisible();
    expect(screen.getByText("56")).toBeVisible();
    expect(
      screen.getByText(/counted from completed goals · 4 min per avoided manual touch/i),
    ).toBeVisible();
  });

  it("renders the daily series with a legend and a table twin", async () => {
    renderWithProviders(<AnalyticsPage />);

    const daily = await screen.findByRole("region", { name: /daily goal activity/i });
    const table = within(daily).getByRole("table", { name: /goals per day/i });
    expect(within(table).getByRole("row", { name: /2026-08-30 9 3 5/i }))
      .toBeInTheDocument();
  });

  it("names the empty window instead of drawing an empty plot", async () => {
    vi.spyOn(api, "outcomeAnalytics").mockResolvedValue({
      outcomes: [],
      daily: [],
      value: { operator_minutes_saved: 0 },
    });
    renderWithProviders(<AnalyticsPage />);

    expect(
      await screen.findByText(/no goals reached an outcome in this window/i),
    ).toBeVisible();
    expect(screen.getByText(/no goals opened in this window/i)).toBeVisible();
  });
});
