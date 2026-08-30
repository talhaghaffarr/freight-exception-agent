import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { GoalListResponse, GoalRow } from "@/app/types";
import { GoalsPage } from "@/features/goals/GoalsPage";
import { renderWithProviders } from "@/test/render";

function row(overrides: Partial<GoalRow> = {}): GoalRow {
  return {
    id: "aaaaaaaa-1111-5111-8111-111111111111",
    reference: "LD-2100",
    agent_type: "late_pickup",
    agent_version: "1.0.0",
    subject_label: "Pickup · Indianapolis, IN",
    state: "succeeded",
    terminal_outcome: "acted_successfully",
    opened_at: "2026-08-30T09:12:00+00:00",
    closed_at: "2026-08-30T09:16:00+00:00",
    ...overrides,
  };
}

const RESPONSE: GoalListResponse = {
  rows: [
    row(),
    row({
      id: "bbbbbbbb-2222-5222-8222-222222222222",
      reference: "LD-2101",
      subject_label: "Pickup · St. Louis, MO",
      state: "needs_review",
      terminal_outcome: null,
      closed_at: null,
    }),
  ],
  counts: { succeeded: 14, suppressed: 25, needs_review: 1 },
};

describe("GoalsPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "listGoals").mockResolvedValue(RESPONSE);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists goals with operator language, never a bare enum", async () => {
    renderWithProviders(<GoalsPage />);

    const queue = await screen.findByRole("region", { name: /goal queue/i });
    expect(await within(queue).findByText("LD-2100")).toBeVisible();
    expect(within(queue).getByText("Acted successfully")).toBeVisible();
    expect(within(queue).getByText("Pickup · Indianapolis, IN")).toBeVisible();
    expect(within(queue).queryByText("acted_successfully")).not.toBeInTheDocument();
  });

  it("links every row to its trace", async () => {
    renderWithProviders(<GoalsPage />);

    const link = await screen.findByRole("link", { name: "LD-2100" });
    expect(link).toHaveAttribute(
      "href",
      "/goals/aaaaaaaa-1111-5111-8111-111111111111",
    );
  });

  it("shows whole-tenant counts on the filter chips", async () => {
    renderWithProviders(<GoalsPage />);

    const filter = await screen.findByRole("navigation", { name: /filter goals/i });
    expect(
      await within(filter).findByRole("button", { name: /succeeded 14/i }),
    ).toBeVisible();
    expect(within(filter).getByRole("button", { name: /all 40/i })).toBeVisible();
  });

  it("filters by state and keeps the choice in the URL", async () => {
    const user = userEvent.setup();
    renderWithProviders(<GoalsPage />);

    await user.click(await screen.findByRole("button", { name: /succeeded 14/i }));

    expect(api.listGoals).toHaveBeenLastCalledWith("atlas-brokerage", {
      state: "succeeded",
    });
    expect(screen.getByRole("button", { name: /succeeded 14/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("reads the state filter back from the URL on load", async () => {
    renderWithProviders(<GoalsPage />, { route: "/goals?state=needs_review" });

    await screen.findByRole("region", { name: /goal queue/i });
    expect(api.listGoals).toHaveBeenCalledWith("atlas-brokerage", {
      state: "needs_review",
    });
  });

  it("names the empty state instead of showing a blank table", async () => {
    vi.spyOn(api, "listGoals").mockResolvedValue({
      rows: [],
      counts: { succeeded: 14 },
    });
    renderWithProviders(<GoalsPage />, { route: "/goals?state=failed" });

    expect(await screen.findByText(/no goals in “failed”/i)).toBeVisible();
  });
});
