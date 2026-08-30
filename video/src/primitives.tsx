/**
 * Shared building blocks for the walkthrough scenes.
 *
 * Every animation here is driven by the frame, never by wall-clock time or
 * randomness, so a re-render is byte-identical.
 */

import type { CSSProperties, ReactNode } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

import { theme } from "./theme";

export const SANS = '"Barlow", system-ui, sans-serif';
export const DISPLAY = '"Barlow Condensed", "Barlow", sans-serif';
export const MONO = '"IBM Plex Mono", ui-monospace, monospace';

/** Fade and lift, the one entrance used throughout. */
export function Rise({
  delay = 0,
  children,
  style,
}: {
  delay?: number;
  children: ReactNode;
  style?: CSSProperties;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: 22 });

  return (
    <div
      style={{
        opacity: progress,
        transform: `translateY(${interpolate(progress, [0, 1], [18, 0])}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** A number that counts up to its value, for the board counters. */
export function CountUp({ to, delay = 0 }: { to: number; delay?: number }) {
  const frame = useCurrentFrame();
  const value = Math.round(
    interpolate(frame - delay, [0, 26], [0, to], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  return <>{value}</>;
}

export function Chip({
  tone,
  children,
}: {
  tone: "red" | "amber" | "green" | "slate" | "brand";
  children: ReactNode;
}) {
  const tones = {
    red: [theme.redSoft, theme.red],
    amber: [theme.amberSoft, theme.amber],
    green: [theme.greenSoft, theme.green],
    slate: [theme.slateSoft, theme.slate],
    brand: [theme.brandSoft, theme.brand],
  } as const;
  const [background, color] = tones[tone];

  return (
    <span
      style={{
        background,
        color,
        fontFamily: SANS,
        fontWeight: 600,
        fontSize: 22,
        padding: "6px 16px",
        borderRadius: 999,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

/** The caption strip that names what the viewer is looking at. */
export function SceneLabel({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <Rise>
      <div
        style={{
          fontFamily: DISPLAY,
          fontSize: 24,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: theme.brand,
          fontWeight: 600,
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          fontFamily: DISPLAY,
          fontSize: 68,
          lineHeight: 1.02,
          fontWeight: 600,
          color: theme.text,
          textTransform: "uppercase",
          marginTop: 6,
        }}
      >
        {title}
      </div>
    </Rise>
  );
}

export function Card({
  children,
  style,
  delay = 0,
}: {
  children: ReactNode;
  style?: CSSProperties;
  delay?: number;
}) {
  return (
    <Rise delay={delay}>
      <div
        style={{
          background: theme.surface,
          borderRadius: 14,
          border: `1px solid ${theme.border}`,
          boxShadow: "0 12px 34px rgba(24,34,48,0.10)",
          overflow: "hidden",
          ...style,
        }}
      >
        {children}
      </div>
    </Rise>
  );
}

/** A labelled figure, matching the console's fact grid. */
export function Fact({
  label,
  value,
  note,
  tone,
  delay = 0,
}: {
  label: string;
  value: string;
  note?: string;
  tone?: "red" | "muted";
  delay?: number;
}) {
  return (
    <Rise delay={delay} style={{ flex: 1, padding: "22px 26px" }}>
      <div
        style={{
          fontFamily: SANS,
          fontSize: 18,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: theme.textMute,
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: tone === "muted" ? 30 : 40,
          fontWeight: 600,
          letterSpacing: "-0.02em",
          marginTop: 8,
          color: tone === "red" ? theme.red : tone === "muted" ? theme.textMute : theme.text,
        }}
      >
        {value}
      </div>
      {note ? (
        <div style={{ fontFamily: SANS, fontSize: 18, color: theme.textMute, marginTop: 4 }}>
          {note}
        </div>
      ) : null}
    </Rise>
  );
}

export function Scene({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: theme.ground,
        padding: "72px 96px",
        display: "flex",
        flexDirection: "column",
        gap: 40,
        fontFamily: SANS,
      }}
    >
      {children}
    </div>
  );
}
