/**
 * The six scenes of the walkthrough.
 *
 * Every figure shown here is one the running system produces: LD-1048 is 38
 * minutes late against a 30-minute threshold, LD-1051 has no computable ETA,
 * and the racing scanners resolve to one goal. Nothing is dramatised.
 */

import { interpolate, useCurrentFrame } from "remotion";

import { Card, Chip, CountUp, DISPLAY, Fact, MONO, Rise, SANS, Scene, SceneLabel } from "./primitives";
import { theme } from "./theme";

/* ------------------------------------------------------------------ Title */

export function TitleScene() {
  const frame = useCurrentFrame();
  const rule = interpolate(frame, [12, 42], [0, 420], { extrapolateRight: "clamp" });

  return (
    <Scene>
      <div style={{ margin: "auto", textAlign: "center" }}>
        <Rise>
          <div
            style={{
              fontFamily: DISPLAY,
              fontSize: 132,
              fontWeight: 700,
              color: theme.text,
              letterSpacing: "0.01em",
              textTransform: "uppercase",
              lineHeight: 1,
            }}
          >
            RelayOps
          </div>
        </Rise>
        <div style={{ height: 3, width: rule, background: theme.brand, margin: "26px auto" }} />
        <Rise delay={16}>
          <div style={{ fontFamily: SANS, fontSize: 34, color: theme.textDim, maxWidth: 1000 }}>
            A late pickup, detected from freight facts and acted on exactly once.
          </div>
        </Rise>
        <Rise delay={30} style={{ marginTop: 34 }}>
          <Chip tone="amber">Sandbox · synthetic data · no external sends</Chip>
        </Rise>
      </div>
    </Scene>
  );
}

/* ------------------------------------------------------------------ Board */

const COUNTERS = [
  { value: 5, label: "Needs action", note: "Prioritized", flag: true },
  { value: 1, label: "Late pickup", note: "Past threshold" },
  { value: 4, label: "No signal", note: "Tracking stale" },
  { value: 36, label: "Not started", note: "Pre-pickup" },
];

export function BoardScene() {
  return (
    <Scene>
      <SceneLabel eyebrow="Live load control" title="48 active truckloads" />

      <Card style={{ display: "flex" }} delay={10}>
        {COUNTERS.map((counter, index) => (
          <div
            key={counter.label}
            style={{
              flex: 1,
              padding: "26px 30px",
              borderRight: index === COUNTERS.length - 1 ? "none" : `1px solid ${theme.border}`,
              borderTop: `4px solid ${counter.flag ? theme.brand : "transparent"}`,
            }}
          >
            <div
              style={{
                fontFamily: DISPLAY,
                fontSize: 76,
                fontWeight: 600,
                lineHeight: 0.9,
                color: theme.text,
              }}
            >
              <CountUp to={counter.value} delay={22 + index * 5} />
            </div>
            <div style={{ fontFamily: SANS, fontSize: 24, fontWeight: 600, marginTop: 10 }}>
              {counter.label}
            </div>
            <div style={{ fontFamily: SANS, fontSize: 20, color: theme.textMute }}>{counter.note}</div>
          </div>
        ))}
      </Card>

      <Rise delay={60}>
        <div style={{ fontFamily: SANS, fontSize: 30, color: theme.textDim, maxWidth: 1300 }}>
          Forty-eight loads, five that need a person. The board's job is to make those five
          obvious — and to be honest about the four it cannot see.
        </div>
      </Rise>
    </Scene>
  );
}

/* ------------------------------------------------------------------ Facts */

export function FactsScene() {
  return (
    <Scene>
      <SceneLabel eyebrow="LD-1048 · Chicago → Dallas" title="Computed, not asserted" />

      <Card delay={10}>
        <div style={{ display: "flex", borderBottom: `1px solid ${theme.border}` }}>
          <Fact label="Pickup appointment" value="10:40 PM" note="revision 3" delay={16} />
          <Fact label="Computed ETA" value="11:18 PM" note="historical average" delay={26} />
          <Fact label="Risk" value="+38 min" note="threshold 30 min" tone="red" delay={36} />
          <Fact label="Tracking" value="Fresh" note="2m ago · Springfield, MO" delay={46} />
        </div>
        <div style={{ padding: "22px 26px", background: theme.sunken }}>
          <Rise delay={62}>
            <div style={{ fontFamily: MONO, fontSize: 22, color: theme.textDim }}>
              now 22:43 + remaining route 55m = 23:18 · appointment 22:40 → 38 minutes late
            </div>
          </Rise>
        </div>
      </Card>

      <Rise delay={80}>
        <div style={{ fontFamily: SANS, fontSize: 30, color: theme.textDim, maxWidth: 1300 }}>
          Arithmetic over a recorded position and a route estimate. No model is consulted, and
          the evidence timestamp travels with the number.
        </div>
      </Rise>
    </Scene>
  );
}

/* ----------------------------------------------------------------- Ledger */

const CHECKS = [
  ["Pickup open", "not completed"],
  ["Appointment on file", "10:40 PM · rev 3"],
  ["Tracking fresh", "latest fix fresh"],
  ["ETA computed", "11:18 PM · route_estimate"],
  ["Threshold exceeded", "38 min vs 30 min"],
  ["Recipient verified", "dana.reyes@atlasbrokerage.demo"],
  ["No prior action", "none for this episode"],
];

export function LedgerScene() {
  const frame = useCurrentFrame();

  return (
    <Scene>
      <SceneLabel eyebrow="Agent decision" title="It shows its work" />

      <Card delay={8} style={{ padding: "30px 40px" }}>
        <div style={{ position: "relative", paddingLeft: 34 }}>
          {/* The spine, drawn as the checks land. */}
          <div
            style={{
              position: "absolute",
              left: 8,
              top: 10,
              width: 2,
              height: interpolate(frame, [18, 150], [0, CHECKS.length * 62 - 20], {
                extrapolateRight: "clamp",
                extrapolateLeft: "clamp",
              }),
              background: theme.border,
            }}
          />
          {CHECKS.map(([label, detail], index) => (
            <Rise key={label} delay={20 + index * 18} style={{ height: 62 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
                <span
                  style={{
                    position: "absolute",
                    /* The Rise transform makes this row the containing block,
                       so the spine at container-x 8 is row-x 34-26. */
                    left: -26,
                    width: 18,
                    height: 18,
                    borderRadius: 999,
                    background: theme.green,
                    color: "#fff",
                    fontSize: 12,
                    display: "grid",
                    placeItems: "center",
                    fontFamily: MONO,
                    fontWeight: 700,
                  }}
                >
                  ✓
                </span>
                <span style={{ fontFamily: SANS, fontSize: 27, fontWeight: 500 }}>{label}</span>
                <span style={{ fontFamily: MONO, fontSize: 20, color: theme.textMute }}>
                  {detail}
                </span>
              </div>
            </Rise>
          ))}
        </div>
      </Card>

      <Rise delay={170}>
        <div
          style={{
            background: theme.brandSoft,
            borderRadius: 12,
            padding: "20px 28px",
            display: "inline-flex",
            gap: 14,
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontFamily: DISPLAY,
              fontSize: 28,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: theme.brand,
            }}
          >
            Next
          </span>
          <span style={{ fontFamily: SANS, fontSize: 28, color: theme.text }}>
            enqueue one deduplicated notification
          </span>
        </div>
      </Rise>
    </Scene>
  );
}

/* ---------------------------------------------------------------- Unknown */

export function UnknownScene() {
  return (
    <Scene>
      <SceneLabel eyebrow="LD-1051 · Detroit → Nashville" title="Unknown is an answer" />

      <Card delay={10}>
        <div style={{ display: "flex", borderBottom: `1px solid ${theme.border}` }}>
          <Fact label="Pickup appointment" value="11:10 PM" delay={16} />
          <Fact label="Computed ETA" value="Unknown" note="Tracking stale" tone="muted" delay={26} />
          <Fact label="Risk" value="—" note="not evaluable" tone="muted" delay={36} />
          <Fact label="Tracking" value="Stale" note="42m ago" delay={46} />
        </div>
        <div style={{ padding: "24px 26px", background: theme.ink }}>
          <Rise delay={64}>
            <pre
              style={{
                fontFamily: MONO,
                fontSize: 24,
                color: theme.onInk,
                margin: 0,
                lineHeight: 1.5,
              }}
            >
{`{ "predicted_arrival": null,
  "reason": "tracking_stale" }`}
            </pre>
          </Rise>
        </div>
      </Card>

      <Rise delay={92}>
        <div style={{ fontFamily: SANS, fontSize: 30, color: theme.textDim, maxWidth: 1360 }}>
          The position is 42 minutes old, past the tenant's maximum. Rather than estimate, the
          agent suppresses the alert and records <span style={{ fontFamily: MONO, color: theme.onInk, background: theme.ink, padding: "2px 8px", borderRadius: 6 }}>tracking_stale</span> as
          a countable outcome. A silent non-action would be indistinguishable from a bug.
        </div>
      </Rise>
    </Scene>
  );
}

/* ------------------------------------------------------------------- Race */

export function RaceScene() {
  const frame = useCurrentFrame();
  const settled = frame > 120;

  return (
    <Scene>
      <SceneLabel eyebrow="Concurrency" title="Two scanners, one goal" />

      <Rise delay={8}>
        <div style={{ fontFamily: SANS, fontSize: 30, color: theme.textDim, maxWidth: 1400 }}>
          Two connections meet at a barrier and issue the same INSERT.
        </div>
      </Rise>

      <Card delay={22}>
        {[
          { worker: "scanner-A", verdict: "INSERT", meta: "bd97601d · 2.98ms", won: true },
          { worker: "scanner-B", verdict: "UNIQUE CONFLICT", meta: "bd97601d · 5.96ms", won: false },
        ].map((attempt, index) => (
          <Rise
            key={attempt.worker}
            delay={34 + index * 22}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 30,
              padding: "26px 34px",
              borderBottom: index === 0 ? `1px solid ${theme.border}` : "none",
            }}
          >
            <span style={{ fontFamily: MONO, fontSize: 30, fontWeight: 600, width: 220 }}>
              {attempt.worker}
            </span>
            <span
              style={{
                fontFamily: DISPLAY,
                fontSize: 36,
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: attempt.won ? theme.green : theme.red,
                flex: 1,
              }}
            >
              {attempt.verdict}
            </span>
            <span style={{ fontFamily: MONO, fontSize: 22, color: theme.textMute }}>
              {attempt.meta}
            </span>
          </Rise>
        ))}
      </Card>

      {settled ? (
        <Card delay={124} style={{ display: "flex" }}>
          <Fact label="Goals created" value="1" delay={130} />
          <Fact label="Opened events" value="1" delay={138} />
          <Fact label="Duplicates prevented" value="1" delay={146} />
          <Fact label="Enforced by" value="goals_idempotency_key" tone="muted" delay={154} />
        </Card>
      ) : null}

      <Rise delay={186}>
        <div style={{ fontFamily: SANS, fontSize: 30, color: theme.textDim, maxWidth: 1400 }}>
          Both callers receive the same goal id. Correctness comes from the database, not from a
          worker remembering what it did — so a retry, a redelivery, or a second scanner cannot
          double-send.
        </div>
      </Rise>
    </Scene>
  );
}

/* ------------------------------------------------------------------ Close */

export function CloseScene() {
  return (
    <Scene>
      <div style={{ margin: "auto", textAlign: "center", maxWidth: 1400 }}>
        <Rise>
          <div
            style={{
              fontFamily: DISPLAY,
              fontSize: 78,
              fontWeight: 600,
              color: theme.text,
              textTransform: "uppercase",
              lineHeight: 1.05,
            }}
          >
            Facts are computed.<br />Prose is generated.
          </div>
        </Rise>
        <Rise delay={22}>
          <div style={{ fontFamily: SANS, fontSize: 30, color: theme.textDim, marginTop: 28 }}>
            Notification delivery, the Celery dispatch path and the inbound email agent are
            specified and not yet built.
          </div>
        </Rise>
        <Rise delay={44}>
          <div style={{ fontFamily: MONO, fontSize: 34, fontWeight: 600, color: theme.brand, marginTop: 40 }}>
            relayops-demo.onrender.com
          </div>
          <div style={{ fontFamily: MONO, fontSize: 22, color: theme.textMute, marginTop: 12 }}>
            github.com/talhaghaffarr/freight-exception-agent
          </div>
        </Rise>
      </div>
    </Scene>
  );
}
