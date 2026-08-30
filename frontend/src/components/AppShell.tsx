/**
 * The operator shell: navigation rail, header, and the routed workspace.
 *
 * Two rules drive the markup. Controls a role may not use are absent, not
 * disabled — a disabled button still advertises a capability. And the safe-send
 * mode is stated in words wherever it appears, because "can this reach a real
 * customer?" is the most consequential thing on the screen.
 */

import { Menu, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { NAV_ITEMS } from "@/app/navigation";
import { ALL_TENANTS, useSession } from "@/app/session";
import type { EnvironmentMode, HealthReport } from "@/app/types";
import { StatusBadge } from "@/components/StatusBadge";

import { SandboxNotice } from "./SandboxNotice";

import "./AppShell.css";

const ENVIRONMENT_COPY: Record<EnvironmentMode, { label: string; title: string }> = {
  sandbox: {
    label: "Sandbox",
    title: "Sandbox: every message routes to local providers. Nothing leaves this machine.",
  },
  allowlist: {
    label: "Allowlist",
    title: "Allowlist: live providers may send only to the configured test recipients.",
  },
  live: {
    label: "Live",
    title: "Live: enabled tenants can send to real recipients. Messages leave this machine.",
  },
};

function PlatformHealth({ health }: { health: HealthReport | undefined }) {
  if (!health) {
    return (
      <div className="shell-health" data-testid="platform-health">
        <StatusBadge status="unknown" size="sm" label="Health unknown" />
      </div>
    );
  }

  const impaired = health.components.filter((component) => component.status !== "healthy");
  const summary =
    impaired.length === 0
      ? "All components healthy"
      : `${impaired.length} component${impaired.length === 1 ? "" : "s"} impaired`;

  return (
    <div className="shell-health" data-testid="platform-health">
      <StatusBadge status={health.status} size="sm" />
      <span className="shell-health__summary">{summary}</span>
    </div>
  );
}

export interface AppShellProps {
  children: ReactNode;
  health?: HealthReport;
}

export function AppShell({ children, health }: AppShellProps) {
  const { session, activeTenantSlug, setActiveTenantSlug } = useSession();
  const [railExpanded, setRailExpanded] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  const isPlatformOperator = session?.user.is_platform_operator ?? false;
  const environment = ENVIRONMENT_COPY[session?.environment_mode ?? "sandbox"];

  const tenantOptions = useMemo(() => {
    const options = (session?.tenants ?? []).map((tenant) => ({
      value: tenant.slug,
      label: tenant.name,
    }));
    return isPlatformOperator
      ? [{ value: ALL_TENANTS, label: "All tenants" }, ...options]
      : options;
  }, [session, isPlatformOperator]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typingInAField =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;
      if (event.key === "/" && !typingInAField) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="shell" data-rail={railExpanded ? "expanded" : "collapsed"}>
      <a className="skip-link" href="#workspace">
        Skip to main content
      </a>

      <nav className="shell-rail" aria-label="Primary">
        <div className="shell-rail__brand">
          <button
            type="button"
            className="shell-rail__toggle"
            aria-expanded={railExpanded}
            aria-label={railExpanded ? "Collapse navigation" : "Expand navigation"}
            onClick={() => setRailExpanded((open) => !open)}
          >
            <Menu size={18} aria-hidden />
          </button>
          <span className="shell-rail__wordmark">RelayOps</span>
        </div>

        <ul className="shell-rail__list">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `shell-rail__link${isActive ? " is-active" : ""}`
                  }
                  data-nav-id={item.id}
                >
                  <Icon size={18} aria-hidden />
                  <span className="shell-rail__label">{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      <header className="shell-header">
        <div className="shell-header__left">
          <label className="visually-hidden" htmlFor="tenant-switcher">
            Tenant
          </label>
          <select
            id="tenant-switcher"
            className="shell-tenant"
            value={activeTenantSlug ?? ""}
            onChange={(event) => setActiveTenantSlug(event.target.value)}
          >
            {tenantOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <div className="shell-search">
            <Search size={15} aria-hidden />
            <input
              ref={searchRef}
              id="global-search"
              type="search"
              role="searchbox"
              aria-label="Search loads, goals, and messages"
              placeholder="Search load, BOL, driver, goal, email, phone"
            />
            <kbd className="shell-search__hint" aria-hidden>
              /
            </kbd>
          </div>
        </div>

        <div className="shell-header__right">
          <span
            className="shell-environment"
            data-testid="environment-badge"
            data-mode={session?.environment_mode ?? "sandbox"}
            title={environment.title}
          >
            {environment.label}
          </span>

          <PlatformHealth health={health} />

          {isPlatformOperator && (
            <button type="button" className="shell-button">
              Pause all agents
            </button>
          )}

          <span className="shell-user" title={session?.user.email}>
            {session?.user.display_name ?? "Signed out"}
          </span>
        </div>
      </header>

      <main className="shell-workspace" id="workspace" tabIndex={-1}>
        {children}
      </main>

      <SandboxNotice />
    </div>
  );
}
