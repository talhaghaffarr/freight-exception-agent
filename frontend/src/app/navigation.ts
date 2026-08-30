import {
  Activity,
  BarChart3,
  Boxes,
  Inbox,
  LayoutDashboard,
  ListChecks,
  MessagesSquare,
  PlayCircle,
  ServerCog,
} from "lucide-react";
import type { ComponentType } from "react";

export interface NavItem {
  id: string;
  label: string;
  to: string;
  icon: ComponentType<{ size?: number | string; "aria-hidden"?: boolean }>;
  /** Screens an increment has not filled in yet still appear, marked as such. */
  placeholder?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: "Overview", to: "/", icon: LayoutDashboard },
  { id: "live-operations", label: "Live Operations", to: "/live", icon: Activity, placeholder: true },
  { id: "goals", label: "Goals", to: "/goals", icon: ListChecks, placeholder: true },
  { id: "inbox", label: "Inbox", to: "/inbox", icon: Inbox, placeholder: true },
  { id: "agents", label: "Agents", to: "/agents", icon: Boxes, placeholder: true },
  {
    id: "communications",
    label: "Communications",
    to: "/communications",
    icon: MessagesSquare,
    placeholder: true,
  },
  { id: "analytics", label: "Analytics", to: "/analytics", icon: BarChart3, placeholder: true },
  { id: "system", label: "System", to: "/system", icon: ServerCog },
  { id: "simulator", label: "Simulator", to: "/simulator", icon: PlayCircle, placeholder: true },
];
