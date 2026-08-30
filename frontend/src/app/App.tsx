/**
 * Application root.
 *
 * The session gate is the only place that decides between the sign-in screen
 * and the console. Health is polled here so every screen shares one answer.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/app/api";
import { AppRoutes } from "@/app/router";
import { useSession } from "@/app/session";
import { AppShell } from "@/components/AppShell";
import { DemoSignIn } from "@/features/auth/DemoSignIn";
import { OverviewPage } from "@/features/overview/OverviewPage";
import { SystemHealthPage } from "@/features/system/SystemHealthPage";

const HEALTH_POLL_MS = 15_000;

export function App() {
  const { status, activeTenantSlug } = useSession();

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: HEALTH_POLL_MS,
    enabled: status === "authenticated",
  });

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", activeTenantSlug],
    queryFn: () => api.dashboard(activeTenantSlug),
    enabled: status === "authenticated",
  });

  if (status === "loading") {
    return (
      <main className="signin" aria-busy="true">
        <p>Loading RelayOps…</p>
      </main>
    );
  }

  if (status === "anonymous") {
    return <DemoSignIn />;
  }

  return (
    <AppShell health={healthQuery.data}>
      <AppRoutes
        overview={
          <OverviewPage
            dashboard={dashboardQuery.data}
            isLoading={dashboardQuery.isPending}
          />
        }
        system={
          <SystemHealthPage
            health={healthQuery.data}
            isLoading={healthQuery.isPending}
            error={healthQuery.error ? healthQuery.error.message : null}
          />
        }
      />
    </AppShell>
  );
}
