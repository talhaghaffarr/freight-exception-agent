import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

import { SessionContext, type SessionValue } from "@/app/session";
import type { HealthReport, Session } from "@/app/types";

export const atlasTenant = {
  id: "11111111-1111-5111-8111-111111111111",
  slug: "atlas-brokerage",
  name: "Atlas Brokerage",
  timezone: "America/Chicago",
};

export const meridianTenant = {
  id: "22222222-2222-5222-8222-222222222222",
  slug: "meridian-freight",
  name: "Meridian Freight",
  timezone: "America/Los_Angeles",
};

export function buildSession(overrides: Partial<Session> = {}): Session {
  return {
    user: {
      id: "99999999-9999-5999-8999-999999999999",
      email: "reviewer@relayops.demo",
      display_name: "Read-only Reviewer",
      is_platform_operator: false,
    },
    tenants: [atlasTenant, meridianTenant],
    roles: { "atlas-brokerage": "reviewer", "meridian-freight": "reviewer" },
    environment_mode: "sandbox",
    ...overrides,
  };
}

export function buildHealth(overrides: Partial<HealthReport> = {}): HealthReport {
  return {
    status: "healthy",
    ready: true,
    checked_at: "2026-08-30T12:00:00+00:00",
    components: [
      {
        name: "database",
        status: "healthy",
        required: true,
        detail: null,
        latency_ms: 3.1,
        checked_at: "2026-08-30T12:00:00+00:00",
        metadata: {},
      },
    ],
    ...overrides,
  };
}

export function makeSessionValue(overrides: Partial<SessionValue> = {}): SessionValue {
  const session = overrides.session === undefined ? buildSession() : overrides.session;
  return {
    session,
    status: "authenticated",
    activeTenantSlug: session?.tenants[0]?.slug ?? null,
    setActiveTenantSlug: () => {},
    signIn: async () => {},
    signOut: async () => {},
    ...overrides,
  };
}

export function renderWithProviders(
  ui: ReactElement,
  options: { session?: Partial<SessionValue>; route?: string } = {},
): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const value = makeSessionValue(options.session ?? {});

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[options.route ?? "/"]}>
        <QueryClientProvider client={queryClient}>
          <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  }

  return render(ui, { wrapper: Wrapper });
}

/**
 * Axe for an isolated component.
 *
 * The `region` rule asks whether all page content sits inside a landmark. That
 * is a page-level question and is asserted in the AppShell test, where the
 * landmarks actually live; applied to a bare badge it only reports that the
 * badge is not a whole page.
 */
export const componentAxeOptions = { rules: { region: { enabled: false } } } as const;
