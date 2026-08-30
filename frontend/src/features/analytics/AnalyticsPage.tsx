/**
 * Outcome analytics: every reason an agent did or did not act.
 *
 * The charts are inline SVG computed from the API payload — no chart library,
 * no invented smoothing. Colour is status, not decoration: green marks the
 * goals where the agent acted, slate marks the ones it declined, marine blue
 * counts the work that was opened. Every chart has a screen-reader table twin
 * carrying the same numbers.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/app/api";
import { useSession } from "@/app/session";
import type { DailyGoalCounts, OutcomeSlice } from "@/app/types";
import { outcomeLabel } from "@/features/goals/labels";
import "./Analytics.css";

const WINDOW_DAYS = 7;

/** A bar with a 4px rounded data-end and a square baseline edge. */
function rightRoundedBar(x: number, y: number, width: number, height: number): string {
  const r = Math.min(4, width);
  return [
    `M ${x} ${y}`,
    `h ${Math.max(width - r, 0)}`,
    `a ${r} ${r} 0 0 1 ${r} ${r}`,
    `v ${height - 2 * r}`,
    `a ${r} ${r} 0 0 1 ${-r} ${r}`,
    `h ${-Math.max(width - r, 0)}`,
    "z",
  ].join(" ");
}

function topRoundedBar(x: number, y: number, width: number, height: number): string {
  const r = Math.min(4, height, width / 2);
  return [
    `M ${x} ${y + height}`,
    `v ${-(height - r)}`,
    `a ${r} ${r} 0 0 1 ${r} ${-r}`,
    `h ${width - 2 * r}`,
    `a ${r} ${r} 0 0 1 ${r} ${r}`,
    `v ${height - r}`,
    "z",
  ].join(" ");
}

/** Clean tick steps so the mono axis reads 0 / 5 / 10, never 0 / 3.7 / 7.4. */
function tickSteps(max: number): number[] {
  const step = [1, 2, 5, 10, 20, 50].find((candidate) => max / candidate <= 4) ?? 100;
  const ticks: number[] = [];
  for (let value = 0; value <= max; value += step) ticks.push(value);
  return ticks;
}

function OutcomeBars({ outcomes }: { outcomes: OutcomeSlice[] }) {
  const rowHeight = 40;
  const gutter = 224;
  const plotWidth = 380;
  const axisBand = 24;
  const width = gutter + plotWidth + 56;
  const height = outcomes.length * rowHeight + axisBand;
  const max = Math.max(...outcomes.map((slice) => slice.count));
  const ticks = tickSteps(max);
  const scale = (value: number) => (value / (ticks.at(-1) || 1)) * plotWidth;

  return (
    <>
      <svg
        className="chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Outcomes over the last ${WINDOW_DAYS} days, largest first: ${outcomes
          .map((slice) => `${outcomeLabel(slice.outcome)} ${slice.count}`)
          .join(", ")}.`}
      >
        {/* Hairline grid under the marks. */}
        {ticks.map((tick) => (
          <line
            key={tick}
            className="chart__grid"
            x1={gutter + scale(tick)}
            x2={gutter + scale(tick)}
            y1={0}
            y2={height - axisBand}
          />
        ))}
        {outcomes.map((slice, index) => {
          const y = index * rowHeight;
          const barY = y + (rowHeight - 14) / 2;
          const acted = slice.outcome === "acted_successfully";
          return (
            <g key={slice.outcome}>
              <title>{`${outcomeLabel(slice.outcome)} — ${slice.count} goals`}</title>
              <text className="chart__label" x={gutter - 12} y={y + 17} textAnchor="end">
                {outcomeLabel(slice.outcome)}
              </text>
              <text className="chart__enum" x={gutter - 12} y={y + 30} textAnchor="end">
                {slice.outcome}
              </text>
              <path
                className={acted ? "chart__bar chart__bar--acted" : "chart__bar"}
                d={rightRoundedBar(gutter, barY, Math.max(scale(slice.count), 2), 14)}
              />
              <text
                className="chart__value"
                x={gutter + scale(slice.count) + 8}
                y={y + 24}
              >
                {slice.count}
              </text>
            </g>
          );
        })}
        {ticks.map((tick) => (
          <text
            key={`tick-${tick}`}
            className="chart__tick"
            x={gutter + scale(tick)}
            y={height - 8}
            textAnchor="middle"
          >
            {tick}
          </text>
        ))}
      </svg>
      <table className="visually-hidden">
        <caption>Goal outcomes over the last {WINDOW_DAYS} days</caption>
        <thead>
          <tr>
            <th scope="col">Outcome</th>
            <th scope="col">Goals</th>
          </tr>
        </thead>
        <tbody>
          {outcomes.map((slice) => (
            <tr key={slice.outcome}>
              <th scope="row">{outcomeLabel(slice.outcome)}</th>
              <td>{slice.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

const DAILY_SERIES = [
  { key: "opened", label: "Opened", barClass: "chart__bar--opened" },
  { key: "succeeded", label: "Acted", barClass: "chart__bar--acted" },
  { key: "suppressed", label: "Declined", barClass: "chart__bar" },
] as const;

function dayLabel(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
}

function DailyBars({ daily }: { daily: DailyGoalCounts[] }) {
  const width = 660;
  const plotHeight = 170;
  const axisBand = 26;
  const gutter = 34;
  const height = plotHeight + axisBand;
  const max = Math.max(1, ...daily.map((day) => day.opened));
  const ticks = tickSteps(max);
  const top = ticks.at(-1) || 1;
  const scale = (value: number) => (value / top) * (plotHeight - 12);

  const groupWidth = (width - gutter) / daily.length;
  const barWidth = Math.min(14, (groupWidth - 16) / DAILY_SERIES.length - 2);

  return (
    <>
      <div className="chart__legend" aria-hidden="true">
        {DAILY_SERIES.map((series) => (
          <span key={series.key} className="chart__legenditem">
            <span className={`chart__swatch chart__swatch--${series.key}`} />
            {series.label}
          </span>
        ))}
      </div>
      <svg
        className="chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Goals per day over the last ${WINDOW_DAYS} days: opened, acted, and declined. Totals: ${daily.reduce((sum, day) => sum + day.opened, 0)} opened.`}
      >
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              className="chart__grid"
              x1={gutter}
              x2={width}
              y1={plotHeight - scale(tick)}
              y2={plotHeight - scale(tick)}
            />
            <text
              className="chart__tick"
              x={gutter - 6}
              y={plotHeight - scale(tick) + 3}
              textAnchor="end"
            >
              {tick}
            </text>
          </g>
        ))}
        {daily.map((day, index) => {
          const groupX =
            gutter +
            index * groupWidth +
            (groupWidth - DAILY_SERIES.length * (barWidth + 2)) / 2;
          return (
            <g key={day.date}>
              <title>{`${dayLabel(day.date)} — opened ${day.opened}, acted ${day.succeeded}, declined ${day.suppressed}`}</title>
              {DAILY_SERIES.map((series, seriesIndex) => {
                const value = day[series.key];
                const barHeight = Math.max(scale(value), value > 0 ? 2 : 0);
                if (barHeight === 0) return null;
                return (
                  <path
                    key={series.key}
                    className={`chart__bar ${series.barClass}`}
                    d={topRoundedBar(
                      groupX + seriesIndex * (barWidth + 2),
                      plotHeight - barHeight,
                      barWidth,
                      barHeight,
                    )}
                  />
                );
              })}
              <text
                className="chart__tick"
                x={gutter + index * groupWidth + groupWidth / 2}
                y={height - 8}
                textAnchor="middle"
              >
                {dayLabel(day.date)}
              </text>
            </g>
          );
        })}
        <line
          className="chart__axis"
          x1={gutter}
          x2={width}
          y1={plotHeight}
          y2={plotHeight}
        />
      </svg>
      <table className="visually-hidden">
        <caption>Goals per day over the last {WINDOW_DAYS} days</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Opened</th>
            <th scope="col">Acted</th>
            <th scope="col">Declined</th>
          </tr>
        </thead>
        <tbody>
          {daily.map((day) => (
            <tr key={day.date}>
              <th scope="row">{day.date}</th>
              <td>{day.opened}</td>
              <td>{day.succeeded}</td>
              <td>{day.suppressed}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function AnalyticsPage() {
  const { activeTenantSlug, session } = useSession();
  // Analytics is always read in one tenant's scope; "all" is not a report view.
  const tenantSlug =
    activeTenantSlug && activeTenantSlug !== "all"
      ? activeTenantSlug
      : (session?.tenants[0]?.slug ?? null);

  const analyticsQuery = useQuery({
    queryKey: ["outcome-analytics", tenantSlug, WINDOW_DAYS],
    queryFn: () => api.outcomeAnalytics(tenantSlug as string, WINDOW_DAYS),
    enabled: Boolean(tenantSlug),
  });

  if (!tenantSlug) {
    return <p className="analytics__empty">Select a tenant to see its outcome report.</p>;
  }

  if (analyticsQuery.isPending) {
    return <p className="analytics__empty">Counting the week's outcomes…</p>;
  }
  if (analyticsQuery.isError) {
    return <p className="analytics__empty">{(analyticsQuery.error as Error).message}</p>;
  }

  const { outcomes, daily, value } = analyticsQuery.data;
  const opened7d = daily.reduce((sum, day) => sum + day.opened, 0);
  const acted7d =
    outcomes.find((slice) => slice.outcome === "acted_successfully")?.count ?? 0;

  return (
    <div className="analytics">
      <header className="analytics__head">
        <div>
          <h1 className="analytics__title">Analytics</h1>
          <p className="analytics__subtitle">
            What the agents did with the last {WINDOW_DAYS} days — and every reason they
            held back.
          </p>
        </div>
      </header>

      <div className="stats">
        <div className="stat stat--value">
          <span className="stat__label">Operator minutes saved</span>
          <span className="stat__value">{value.operator_minutes_saved}</span>
          <span className="stat__note">
            Counted from completed goals · 4 min per avoided manual touch
          </span>
        </div>
        <div className="stat">
          <span className="stat__label">Goals opened · {WINDOW_DAYS} days</span>
          <span className="stat__value">{opened7d}</span>
          <span className="stat__note">Every trigger the scanners picked up</span>
        </div>
        <div className="stat">
          <span className="stat__label">Acted · {WINDOW_DAYS} days</span>
          <span className="stat__value">{acted7d}</span>
          <span className="stat__note">Notifications actually delivered</span>
        </div>
      </div>

      <section className="panel" aria-label="Outcomes">
        <header className="panel__head">
          <h2 className="panel__title">Every reason an agent did or did not act</h2>
          <span className="analytics__window mono">last {WINDOW_DAYS} days</span>
        </header>
        <div className="panel__chart">
          {outcomes.length === 0 ? (
            <p className="analytics__empty">No goals reached an outcome in this window.</p>
          ) : (
            <OutcomeBars outcomes={outcomes} />
          )}
        </div>
      </section>

      <section className="panel" aria-label="Daily goal activity">
        <header className="panel__head">
          <h2 className="panel__title">Goals per day</h2>
          <span className="analytics__window mono">opened · acted · declined</span>
        </header>
        <div className="panel__chart">
          {opened7d === 0 ? (
            <p className="analytics__empty">No goals opened in this window.</p>
          ) : (
            <DailyBars daily={daily} />
          )}
        </div>
      </section>
    </div>
  );
}
