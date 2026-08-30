/**
 * Session boundary.
 *
 * The console never decides what a user may see — it renders what the API says
 * they may see. `roles` and `tenants` come from the server on every load.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, api } from "./api";
import type { Session } from "./types";

export const ALL_TENANTS = "all";

export type SessionStatus = "loading" | "authenticated" | "anonymous";

export interface SessionValue {
  session: Session | null;
  status: SessionStatus;
  activeTenantSlug: string | null;
  setActiveTenantSlug: (slug: string) => void;
  signIn: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const SessionContext = createContext<SessionValue | null>(null);

const ACTIVE_TENANT_STORAGE_KEY = "relayops.activeTenant";

function readStoredTenant(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_TENANT_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [storedTenant, setStoredTenant] = useState<string | null>(readStoredTenant);

  const { data, status: queryStatus } = useQuery({
    queryKey: ["session"],
    queryFn: api.me,
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.status === 401) && failureCount < 2,
    staleTime: 60_000,
  });

  const signInMutation = useMutation({
    mutationFn: api.signIn,
    onSuccess: (session) => queryClient.setQueryData(["session"], session),
  });

  const signOutMutation = useMutation({
    mutationFn: api.signOut,
    onSuccess: () => queryClient.setQueryData(["session"], null),
  });

  const setActiveTenantSlug = useCallback((slug: string) => {
    setStoredTenant(slug);
    try {
      window.localStorage.setItem(ACTIVE_TENANT_STORAGE_KEY, slug);
    } catch {
      /* A private window is not a reason to break tenant switching. */
    }
  }, []);

  const session = data ?? null;

  const activeTenantSlug = useMemo(() => {
    if (!session) return null;
    const available = session.tenants.map((tenant) => tenant.slug);
    if (storedTenant === ALL_TENANTS && session.user.is_platform_operator) {
      return ALL_TENANTS;
    }
    if (storedTenant && available.includes(storedTenant)) return storedTenant;
    return available[0] ?? (session.user.is_platform_operator ? ALL_TENANTS : null);
  }, [session, storedTenant]);

  const value = useMemo<SessionValue>(
    () => ({
      session,
      status:
        queryStatus === "pending" ? "loading" : session ? "authenticated" : "anonymous",
      activeTenantSlug,
      setActiveTenantSlug,
      signIn: async (email: string) => {
        await signInMutation.mutateAsync(email);
      },
      signOut: async () => {
        await signOutMutation.mutateAsync();
      },
    }),
    [session, queryStatus, activeTenantSlug, setActiveTenantSlug, signInMutation, signOutMutation],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used inside a SessionProvider");
  }
  return value;
}
