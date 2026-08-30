import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/AppShell";
import { buildHealth, buildSession, renderWithProviders } from "@/test/render";

function renderShell(options: Parameters<typeof renderWithProviders>[1] = {}) {
  return renderWithProviders(
    <AppShell health={buildHealth()}>
      <p>Workspace content</p>
    </AppShell>,
    options,
  );
}

describe("AppShell", () => {
  it("exposes role-aware primary navigation and environment status", async () => {
    renderShell();

    expect(screen.getByRole("navigation", { name: /primary/i })).toBeVisible();
    expect(screen.getByText("Sandbox")).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /pause all agents/i }),
    ).not.toBeInTheDocument();
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("shows every documented navigation destination", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: /primary/i });
    for (const label of [
      "Overview",
      "Live Operations",
      "Goals",
      "Inbox",
      "Agents",
      "Communications",
      "Analytics",
      "System",
      "Simulator",
    ]) {
      expect(within(nav).getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("offers the global pause control only to a platform operator", () => {
    renderShell({
      session: {
        session: buildSession({
          user: {
            id: "1",
            email: "operator@relayops.demo",
            display_name: "Platform Operator",
            is_platform_operator: true,
          },
        }),
      },
    });
    expect(screen.getByRole("button", { name: /pause all agents/i })).toBeVisible();
  });

  it("hides unauthorized controls rather than disabling them", () => {
    renderShell();
    expect(screen.queryByRole("button", { name: /pause all agents/i })).toBeNull();
  });

  it("lets a member switch between the tenants they belong to", async () => {
    const setActiveTenantSlug = vi.fn();
    renderShell({ session: { setActiveTenantSlug } });

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: /tenant/i }),
      "meridian-freight",
    );
    expect(setActiveTenantSlug).toHaveBeenCalledWith("meridian-freight");
  });

  it("offers the all-tenants scope only to a platform operator", () => {
    const { unmount } = renderShell();
    expect(
      within(screen.getByRole("combobox", { name: /tenant/i })).queryByRole("option", {
        name: /all tenants/i,
      }),
    ).toBeNull();
    unmount();

    renderShell({
      session: {
        session: buildSession({
          user: {
            id: "1",
            email: "operator@relayops.demo",
            display_name: "Platform Operator",
            is_platform_operator: true,
          },
        }),
      },
    });
    expect(
      within(screen.getByRole("combobox", { name: /tenant/i })).getByRole("option", {
        name: /all tenants/i,
      }),
    ).toBeInTheDocument();
  });

  it("names the live safe-send mode unmistakably", () => {
    renderShell({
      session: { session: buildSession({ environment_mode: "live" }) },
    });
    const badge = screen.getByTestId("environment-badge");
    expect(badge).toHaveTextContent("Live");
    expect(badge).toHaveAttribute(
      "title",
      expect.stringContaining("real recipients"),
    );
  });

  it("reports degraded platform health as text, not only as colour", () => {
    renderWithProviders(
      <AppShell
        health={buildHealth({
          status: "degraded",
          components: [
            {
              name: "email",
              status: "unhealthy",
              required: false,
              detail: "cannot reach the SMTP sink on port 1025",
              latency_ms: 1.2,
              checked_at: "2026-08-30T12:00:00+00:00",
              metadata: {},
            },
          ],
        })}
      >
        <p>Workspace content</p>
      </AppShell>,
    );
    const status = screen.getByTestId("platform-health");
    expect(status).toHaveTextContent(/degraded/i);
    expect(status).toHaveTextContent(/1 component/i);
  });

  it("renders the routed workspace content", () => {
    renderShell();
    expect(screen.getByText("Workspace content")).toBeVisible();
  });

  it("gives the search box an accessible name and a keyboard hint", () => {
    renderShell();
    const search = screen.getByRole("searchbox", { name: /search/i });
    expect(search).toHaveAccessibleName();
    expect(screen.getByText("/")).toBeVisible();
  });
});
