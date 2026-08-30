import { screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/StatusBadge";
import { componentAxeOptions, renderWithProviders } from "@/test/render";

describe("StatusBadge", () => {
  it("communicates status with text, not colour alone", () => {
    renderWithProviders(<StatusBadge status="unhealthy" />);
    expect(screen.getByText("Unhealthy")).toBeVisible();
  });

  it("carries a semantic tone attribute for each documented status", () => {
    const cases = [
      ["healthy", "positive"],
      ["degraded", "warning"],
      ["unhealthy", "critical"],
      ["unknown", "neutral"],
      ["waiting", "warning"],
      ["succeeded", "positive"],
      ["failed", "critical"],
      ["suppressed", "neutral"],
      ["needs_review", "warning"],
      ["executing", "info"],
    ] as const;

    for (const [status, tone] of cases) {
      const { unmount } = renderWithProviders(<StatusBadge status={status} />);
      expect(screen.getByTestId(`status-${status}`)).toHaveAttribute("data-tone", tone);
      unmount();
    }
  });

  it("humanises snake_case states", () => {
    renderWithProviders(<StatusBadge status="needs_review" />);
    expect(screen.getByText("Needs review")).toBeVisible();
  });

  it("accepts an explicit label override", () => {
    renderWithProviders(<StatusBadge status="failed" label="Provider attempts exhausted" />);
    expect(screen.getByText("Provider attempts exhausted")).toBeVisible();
  });

  it("has no accessibility violations", async () => {
    renderWithProviders(<StatusBadge status="degraded" />);
    expect(await axe(document.body, componentAxeOptions)).toHaveNoViolations();
  });
});
