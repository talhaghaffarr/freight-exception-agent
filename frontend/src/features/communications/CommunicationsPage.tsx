/**
 * Communications — design preview for Increment 4.
 *
 * A unified outbound/inbound record. Every row carries its goal, tenant, and
 * delivery evidence; a provider that accepted without a receipt is shown as
 * delivery_unknown and reconciled rather than blindly resent.
 */

import { PreviewBanner } from "@/components/PreviewBanner";
import {
  ALL_ENTRIES,
  SAMPLE_TIMELINE,
  type Channel,
  type Direction,
  type TimelineEntry,
} from "./sampleTimeline";
import "./Communications.css";

const STATUS_LABEL: Record<TimelineEntry["status"], string> = {
  delivered: "Delivered",
  delivery_unknown: "Delivery unknown",
  answered: "Answered",
  specified: "Specified",
};

function ChannelIcon({ channel }: { channel: Channel }) {
  const common = {
    width: 16,
    height: 16,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (channel === "email") {
    return (
      <svg {...common}>
        <rect x="2.5" y="5" width="19" height="14" rx="2" />
        <path d="m3.5 7 8.5 6 8.5-6" />
      </svg>
    );
  }
  if (channel === "sms") {
    return (
      <svg {...common}>
        <path d="M21 15a2 2 0 0 1-2 2H8l-4.5 4V5a2 2 0 0 1 2-2H19a2 2 0 0 1 2 2z" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function DirectionArrow({ direction }: { direction: Direction }) {
  const common = {
    width: 14,
    height: 14,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    role: "img" as const,
  };
  if (direction === "out") {
    return (
      <svg {...common} aria-label="Outbound">
        <line x1="7" y1="17" x2="17" y2="7" />
        <polyline points="8 7 17 7 17 16" />
      </svg>
    );
  }
  return (
    <svg {...common} aria-label="Inbound">
      <line x1="17" y1="7" x2="7" y2="17" />
      <polyline points="16 17 7 17 7 8" />
    </svg>
  );
}

function TimelineRow({ entry }: { entry: TimelineEntry }) {
  return (
    <li>
      <div className="comms-row">
        <span className="comms-row__icon">
          <ChannelIcon channel={entry.channel} />
        </span>
        <span className="comms-row__dir">
          <DirectionArrow direction={entry.direction} />
        </span>
        <span className="comms-row__party">{entry.counterparty}</span>
        <span className="comms-row__main">
          <p className="comms-row__summary">{entry.summary}</p>
          {entry.note ? (
            <p
              className={`comms-row__note${
                entry.status === "delivery_unknown" ? " comms-row__note--warning" : ""
              }`}
            >
              {entry.note}
              {entry.status === "delivery_unknown" ? (
                <>
                  {" "}
                  · counted as <code>delivery_unknown</code>
                </>
              ) : null}
            </p>
          ) : null}
        </span>
        <span className="comms-row__goal">
          {entry.goalRef} · {entry.loadRef}
        </span>
        <span className="comms-row__tenant">{entry.tenant}</span>
        <span className="comms-row__time">{entry.time}</span>
        <span className={`comms-chip comms-chip--${entry.status}`}>
          {STATUS_LABEL[entry.status]}
        </span>
      </div>
    </li>
  );
}

export function CommunicationsPage() {
  const counts = {
    all: ALL_ENTRIES.length,
    email: ALL_ENTRIES.filter((entry) => entry.channel === "email").length,
    sms: ALL_ENTRIES.filter((entry) => entry.channel === "sms").length,
    voice: ALL_ENTRIES.filter((entry) => entry.channel === "voice").length,
    attention: ALL_ENTRIES.filter((entry) => entry.status === "delivery_unknown").length,
  };

  const filters = [
    { id: "all", label: "All", count: counts.all, active: true },
    { id: "email", label: "Email", count: counts.email, active: false },
    { id: "sms", label: "SMS", count: counts.sms, active: false },
    { id: "voice", label: "Voice", count: counts.voice, active: false },
    { id: "attention", label: "Needs attention", count: counts.attention, active: false },
  ];

  return (
    <div className="comms">
      <PreviewBanner increment="Increment 4" />

      <header className="comms__head">
        <div>
          <h1 className="comms__title">Communications</h1>
          <p className="comms__subtitle">
            Every message in or out, linked to its load, with delivery evidence.
          </p>
        </div>
      </header>

      <div className="comms-filters" role="group" aria-label="Channel filters">
        {filters.map((filter) => (
          <button
            key={filter.id}
            type="button"
            className="comms-filter"
            aria-pressed={filter.active}
            disabled
            title="Design preview"
          >
            {filter.label}
            <span className="comms-filter__count">{filter.count}</span>
          </button>
        ))}
      </div>

      <section className="comms-panel" aria-label="Communication timeline">
        {SAMPLE_TIMELINE.map((day) => (
          <div key={day.id}>
            <header className="comms-day">
              <h2 className="comms-day__label">{day.label}</h2>
              <span className="comms-day__meta">
                {day.date} · {day.entries.length} entries
              </span>
            </header>
            <ul className="comms-list">
              {day.entries.map((entry) => (
                <TimelineRow key={entry.id} entry={entry} />
              ))}
            </ul>
          </div>
        ))}
      </section>
    </div>
  );
}
