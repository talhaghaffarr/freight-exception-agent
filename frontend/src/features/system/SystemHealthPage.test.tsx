import { screen, within } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

import { SystemHealthPage } from "@/features/system/SystemHealthPage";
import { buildHealth, componentAxeOptions, renderWithProviders } from "@/test/render";

const degraded = buildHealth({
  status: "degraded",
  components: [
    {
      name: "database",
      status: "healthy",
      required: true,
      detail: null,
      latency_ms: 2.4,
      checked_at: "2026-08-30T12:00:00+00:00",
      metadata: { pool_checked_out: 1 },
    },
    {
      name: "email",
      status: "unhealthy",
      required: false,
      detail: "cannot reach the SMTP sink on port 1025",
      latency_ms: 1002.5,
      checked_at: "2026-08-30T12:00:00+00:00",
      metadata: {},
    },
  ],
});

describe("SystemHealthPage", () => {
  it("lists each component with a textual status and its last check time", () => {
    renderWithProviders(<SystemHealthPage health={degraded} />);
    const row = screen.getByRole("row", { name: /database/i });
    expect(within(row).getByText("Healthy")).toBeVisible();
    expect(within(row).getByText(/required/i)).toBeVisible();
    expect(within(row).getByRole("time")).toHaveAttribute(
      "datetime",
      "2026-08-30T12:00:00+00:00",
    );
  });

  it("shows why an impaired component is impaired", () => {
    renderWithProviders(<SystemHealthPage health={degraded} />);
    expect(screen.getByText(/cannot reach the SMTP sink on port 1025/i)).toBeVisible();
  });

  it("distinguishes a degraded platform from an unready one", () => {
    renderWithProviders(<SystemHealthPage health={degraded} />);
    expect(screen.getByTestId("readiness")).toHaveTextContent(/ready to serve traffic/i);
  });

  it("says plainly when a required component makes the platform unready", () => {
    renderWithProviders(
      <SystemHealthPage
        health={buildHealth({
          status: "unhealthy",
          ready: false,
          components: [
            {
              name: "migrations",
              status: "unhealthy",
              required: true,
              detail: "1 migration(s) pending",
              latency_ms: 4,
              checked_at: "2026-08-30T12:00:00+00:00",
              metadata: {},
            },
          ],
        })}
      />,
    );
    expect(screen.getByTestId("readiness")).toHaveTextContent(/not ready/i);
  });

  it("offers no mutation controls to a reviewer", () => {
    renderWithProviders(<SystemHealthPage health={degraded} />);
    expect(screen.queryByRole("button", { name: /restart/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /pause/i })).toBeNull();
  });

  it("has no accessibility violations", async () => {
    renderWithProviders(<SystemHealthPage health={degraded} />);
    expect(await axe(document.body, componentAxeOptions)).toHaveNoViolations();
  });
});
