/**
 * Route table. Every destination in the navigation rail resolves to a screen;
 * screens whose backend has not shipped yet carry a PreviewBanner instead of
 * an empty placeholder.
 */

import type { ReactElement } from "react";
import { Route, Routes } from "react-router-dom";

import { AgentsPage } from "@/features/agents/AgentsPage";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { CommunicationsPage } from "@/features/communications/CommunicationsPage";
import { GoalTracePage } from "@/features/goals/GoalTracePage";
import { GoalsPage } from "@/features/goals/GoalsPage";
import { InboxPage } from "@/features/inbox/InboxPage";
import { LiveOperationsPage } from "@/features/live/LiveOperationsPage";
import { PlaceholderPage } from "@/features/placeholder/PlaceholderPage";
import { SimulatorPage } from "@/features/simulator/SimulatorPage";

export interface AppRoutesProps {
  overview: ReactElement;
  system: ReactElement;
}

export function AppRoutes({ overview, system }: AppRoutesProps) {
  return (
    <Routes>
      <Route path="/" element={overview} />
      <Route path="/system" element={system} />
      <Route path="/live" element={<LiveOperationsPage />} />
      <Route path="/goals" element={<GoalsPage />} />
      <Route path="/goals/:goalId" element={<GoalTracePage />} />
      <Route path="/inbox" element={<InboxPage />} />
      <Route path="/agents" element={<AgentsPage />} />
      <Route path="/communications" element={<CommunicationsPage />} />
      <Route path="/analytics" element={<AnalyticsPage />} />
      <Route path="/simulator" element={<SimulatorPage />} />
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
