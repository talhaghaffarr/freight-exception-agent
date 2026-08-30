import { screen, within } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

import { OverviewPage } from "@/features/overview/OverviewPage";
import { componentAxeOptions, renderWithProviders } from "@/test/render";
import type { Dashboard } from "@/app/types";

const emptyDashboard: Dashboard = {
  agents: [],
  goals: { opened: 0, waiting: 0, needs_review: 0, failed: 0 },
  communications: { email: 0, sms: 0, voice: 0 },
  value: { operator_minutes_saved: 0 },
  recent_activity: [],
};

describe("OverviewPage", () => {
  it("explains the zero state instead of showing invented metrics", () => {
    renderWithProviders(<OverviewPage dashboard={emptyDashboard} />);
    expect(screen.getByRole("heading", { name: /fleet overview/i })).toBeVisible();
    expect(screen.getByText(/no agent has run yet/i)).toBeVisible();
    expect(screen.getByRole("link", { name: /open the simulator/i })).toHaveAttribute(
      "href",
      "/simulator",
    );
  });

  it("counts goals by state without rounding a zero into a dash", () => {
    renderWithProviders(<OverviewPage dashboard={emptyDashboard} />);
    const goals = screen.getByTestId("goals-summary");
    expect(within(goals).getByTestId("goals-opened")).toHaveTextContent("0");
    expect(within(goals).getByTestId("goals-needs_review")).toHaveTextContent("0");
  });

  it("renders real counts when the fleet has done work", () => {
    renderWithProviders(
      <OverviewPage
        dashboard={{
          ...emptyDashboard,
          goals: { opened: 128, waiting: 9, needs_review: 3, failed: 1 },
          communications: { email: 96, sms: 22, voice: 4 },
          value: { operator_minutes_saved: 412 },
          agents: [
            {
              agent_type: "late_pickup_alert",
              version: "1.0.0",
              tenant_slug: "atlas-brokerage",
              enabled: true,
              goals_open: 4,
              success_rate: 0.97,
            },
          ],
        }}
      />,
    );
    expect(screen.getByTestId("goals-opened")).toHaveTextContent("128");
    expect(screen.getByText(/412/)).toBeVisible();
    expect(screen.getByRole("row", { name: /late pickup alert/i })).toBeInTheDocument();
  });

  it("shows a loading state that preserves layout", () => {
    renderWithProviders(<OverviewPage isLoading />);
    expect(screen.getByTestId("overview-skeleton")).toBeVisible();
  });

  it("has no accessibility violations", async () => {
    renderWithProviders(<OverviewPage dashboard={emptyDashboard} />);
    expect(await axe(document.body, componentAxeOptions)).toHaveNoViolations();
  });
});
