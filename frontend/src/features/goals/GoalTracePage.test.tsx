import { screen, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { GoalTrace } from "@/app/types";
import { GoalTracePage } from "@/features/goals/GoalTracePage";
import { renderWithProviders } from "@/test/render";

const GOAL_ID = "aaaaaaaa-1111-5111-8111-111111111111";

const TRACE: GoalTrace = {
  goal: {
    id: GOAL_ID,
    state: "succeeded",
    agent_type: "late_pickup",
    agent_version: "1.0.0",
    trigger_fingerprint: "pickup:stop-1:appointment:1:late:v1:d0",
    terminal_outcome: "acted_successfully",
    opened_at: "2026-08-30T09:12:00+00:00",
  },
  events: [
    {
      sequence: 1,
      event_type: "opened",
      from_state: null,
      to_state: "opened",
      detail: { reference: "LD-2100" },
      occurred_at: "2026-08-30T09:12:00+00:00",
    },
    {
      sequence: 2,
      event_type: "collecting_facts",
      from_state: "opened",
      to_state: "collecting_facts",
      detail: { minutes_late: 38, tracking_age_minutes: 2 },
      occurred_at: "2026-08-30T09:12:40+00:00",
    },
    {
      sequence: 3,
      event_type: "outcome_recorded",
      from_state: "collecting_facts",
      to_state: "succeeded",
      detail: { outcome: "acted_successfully" },
      occurred_at: "2026-08-30T09:13:20+00:00",
    },
  ],
};

function renderTrace() {
  return renderWithProviders(
    <Routes>
      <Route path="/goals/:goalId" element={<GoalTracePage />} />
    </Routes>,
    { route: `/goals/${GOAL_ID}` },
  );
}

describe("GoalTracePage", () => {
  beforeEach(() => {
    vi.spyOn(api, "goalTrace").mockResolvedValue(TRACE);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the event spine in order with human labels first", async () => {
    renderTrace();

    const events = await screen.findByRole("region", { name: /goal events/i });
    const items = within(events).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("Goal opened");
    expect(items[1]).toHaveTextContent("Facts collected");
    expect(items[2]).toHaveTextContent("Outcome recorded");
    // The raw transition stays visible as secondary evidence.
    expect(items[2]).toHaveTextContent("collecting_facts → succeeded");
  });

  it("shows the evidence in each event's detail", async () => {
    renderTrace();

    const events = await screen.findByRole("region", { name: /goal events/i });
    expect(within(events).getByText(/minutes_late/)).toBeVisible();
    expect(within(events).getByText(/38/)).toBeVisible();
  });

  it("presents the fingerprint as under-the-hood proof with a copy affordance", async () => {
    renderTrace();

    expect(
      await screen.findByText("pickup:stop-1:appointment:1:late:v1:d0"),
    ).toBeVisible();
    expect(screen.getByText(/idempotency key/i)).toBeVisible();
    expect(screen.getByRole("button", { name: /copy/i })).toBeVisible();
  });

  it("links back to the goals queue", async () => {
    renderTrace();

    const back = await screen.findByRole("link", { name: /goals/i });
    expect(back).toHaveAttribute("href", "/goals");
  });

  it("asks the API for this tenant and goal", async () => {
    renderTrace();

    await screen.findByRole("region", { name: /goal events/i });
    expect(api.goalTrace).toHaveBeenCalledWith("atlas-brokerage", GOAL_ID);
  });
});
