/**
 * Route table.
 *
 * Every destination in the navigation rail resolves to something today. Screens
 * a later increment owns render a placeholder that names the increment.
 */

import type { ReactElement } from "react";
import { Route, Routes } from "react-router-dom";

import { PlaceholderPage } from "@/features/placeholder/PlaceholderPage";

const PLACEHOLDERS = [
  {
    path: "/live",
    title: "Live Operations",
    increment: "Increment 2",
    description:
      "The priority load board, milestone timeline, and per-load agent activity arrive with the Late Pickup slice.",
  },
  {
    path: "/goals",
    title: "Goals",
    increment: "Increment 2",
    description:
      "The goals queue and the goal trace arrive with the Late Pickup slice.",
  },
  {
    path: "/inbox",
    title: "Reactive Inbox",
    increment: "Increment 3",
    description:
      "Inbound email, the safety gate ladder, and threaded replies arrive with the Reactive Email slice.",
  },
  {
    path: "/agents",
    title: "Agent Catalog",
    increment: "Increment 5",
    description: "Agent capabilities, versions, and tenant adoption arrive with the control plane.",
  },
  {
    path: "/communications",
    title: "Communications",
    increment: "Increment 4",
    description:
      "The unified email, SMS, and voice timeline arrives with the remaining agents and channels.",
  },
  {
    path: "/analytics",
    title: "Analytics",
    increment: "Increment 5",
    description: "Outcome, latency, and value reporting arrives with the control plane.",
  },
  {
    path: "/simulator",
    title: "Scenario Simulator",
    increment: "Increment 5",
    description:
      "Seeded scenarios, virtual time, and injected failures arrive with the control plane.",
  },
] as const;

export interface AppRoutesProps {
  overview: ReactElement;
  system: ReactElement;
}

export function AppRoutes({ overview, system }: AppRoutesProps) {
  return (
    <Routes>
      <Route path="/" element={overview} />
      <Route path="/system" element={system} />
      {PLACEHOLDERS.map((placeholder) => (
        <Route
          key={placeholder.path}
          path={placeholder.path}
          element={
            <PlaceholderPage
              title={placeholder.title}
              increment={placeholder.increment}
              description={placeholder.description}
            />
          }
        />
      ))}
      <Route
        path="*"
        element={
          <PlaceholderPage
            title="Not found"
            increment="this build"
            description="That route does not exist in the console."
          />
        }
      />
    </Routes>
  );
}
