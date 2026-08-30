/**
 * Sample timeline for the Communications design preview.
 *
 * A unified outbound/inbound record across channels and tenants. Delivery is
 * only ever claimed when a receipt exists; provider uncertainty is recorded
 * as delivery_unknown and reconciled, never blindly resent.
 */

export type Channel = "email" | "sms" | "voice";
export type Direction = "out" | "in";
export type EntryStatus = "delivered" | "delivery_unknown" | "answered" | "specified";

export interface TimelineEntry {
  id: string;
  channel: Channel;
  direction: Direction;
  /** Recipient for outbound, sender for inbound. */
  counterparty: string;
  summary: string;
  goalRef: string;
  loadRef: string;
  tenant: string;
  time: string;
  status: EntryStatus;
  note?: string;
}

export interface TimelineDay {
  id: string;
  label: string;
  date: string;
  entries: TimelineEntry[];
}

export const SAMPLE_TIMELINE: TimelineDay[] = [
  {
    id: "today",
    label: "Today",
    date: "Sun Aug 31",
    entries: [
      {
        id: "t-1",
        channel: "email",
        direction: "out",
        counterparty: "dana.reyes@atlasbrokerage.demo",
        summary: "Late pickup alert — LD-1048 running +38 min",
        goalRef: "G-2841",
        loadRef: "LD-1048",
        tenant: "Atlas Brokerage",
        time: "09:22:41",
        status: "delivered",
      },
      {
        id: "t-2",
        channel: "email",
        direction: "out",
        counterparty: "ops@northwindfoods.example",
        summary: "Late pickup alert — LD-1051, tracking stale, ETA unknown",
        goalRef: "G-2844",
        loadRef: "LD-1051",
        tenant: "Atlas Brokerage",
        time: "08:58:03",
        status: "delivery_unknown",
        note: "provider accepted, no receipt — reconciliation pending, no blind resend",
      },
      {
        id: "t-3",
        channel: "email",
        direction: "out",
        counterparty: "dana@acmeretail.example",
        summary: "Re: Where is LD-1048? — computed status reply",
        goalRef: "G-2857",
        loadRef: "LD-1048",
        tenant: "Atlas Brokerage",
        time: "08:47:58",
        status: "delivered",
      },
      {
        id: "t-4",
        channel: "email",
        direction: "in",
        counterparty: "dana@acmeretail.example",
        summary: "Where is LD-1048?",
        goalRef: "G-2857",
        loadRef: "LD-1048",
        tenant: "Atlas Brokerage",
        time: "08:47:12",
        status: "answered",
      },
      {
        id: "t-5",
        channel: "sms",
        direction: "out",
        counterparty: "+1 (555) 014-2287",
        summary: "POD request — delivery complete, document missing",
        goalRef: "G-2861",
        loadRef: "LD-1044",
        tenant: "Atlas Brokerage",
        time: "07:15:20",
        status: "specified",
        note: "channel ships in Increment 4",
      },
    ],
  },
  {
    id: "yesterday",
    label: "Yesterday",
    date: "Sat Aug 30",
    entries: [
      {
        id: "y-1",
        channel: "voice",
        direction: "out",
        counterparty: "+1 (555) 019-4471",
        summary: "ETA confirmation call — computed ETA stale near appointment",
        goalRef: "G-2790",
        loadRef: "LD-7714",
        tenant: "Meridian Freight",
        time: "16:42:07",
        status: "specified",
        note: "channel ships in Increment 4",
      },
      {
        id: "y-2",
        channel: "email",
        direction: "out",
        counterparty: "am.west@meridianfreight.demo",
        summary: "Late pickup alert — LD-7712 running +52 min",
        goalRef: "G-2781",
        loadRef: "LD-7712",
        tenant: "Meridian Freight",
        time: "14:05:33",
        status: "delivered",
      },
      {
        id: "y-3",
        channel: "email",
        direction: "out",
        counterparty: "ops@customer.example",
        summary: "Re: status LD-1029 — computed status reply",
        goalRef: "G-2766",
        loadRef: "LD-1029",
        tenant: "Atlas Brokerage",
        time: "11:31:44",
        status: "delivered",
      },
      {
        id: "y-4",
        channel: "email",
        direction: "in",
        counterparty: "ops@customer.example",
        summary: "status LD-1029?",
        goalRef: "G-2766",
        loadRef: "LD-1029",
        tenant: "Atlas Brokerage",
        time: "11:31:02",
        status: "answered",
      },
    ],
  },
];

export const ALL_ENTRIES: TimelineEntry[] = SAMPLE_TIMELINE.flatMap((day) => day.entries);
