/**
 * The video inherits the console's palette and type so the walkthrough looks
 * like the product rather than like a marketing artefact about it.
 *
 * Light only, matching frontend/src/styles/tokens.css: cool off-white ground,
 * white evidence surfaces, navy-slate ink, one marine-blue accent.
 */

export const theme = {
  ground: "#f4f6f9",
  surface: "#ffffff",
  sunken: "#eef1f5",
  border: "#e2e7ee",
  borderStrong: "#c9d2dd",
  // The one dark surface: code and evidence blocks, matching the nav rail.
  ink: "#16202e",
  onInk: "#e8edf4",
  onInkDim: "#8fa0b5",

  text: "#182230",
  textDim: "#4d5a6b",
  textMute: "#7b8798",

  brand: "#1f5b9e",
  brandStrong: "#174a85",
  brandSoft: "#e8eff7",
  red: "#b3261e",
  redSoft: "#f9e8e6",
  amber: "#96610a",
  amberSoft: "#f7eeda",
  green: "#0e7a55",
  greenSoft: "#e4f2ec",
  slate: "#4d5a6b",
  slateSoft: "#eaeef3",
} as const;

export const FPS = 30;

/** Scene boundaries in frames. The whole piece is 90 seconds. */
export const SCENES = {
  title: { from: 0, durationInFrames: 150 },
  board: { from: 150, durationInFrames: 390 },
  facts: { from: 540, durationInFrames: 450 },
  ledger: { from: 990, durationInFrames: 510 },
  unknown: { from: 1500, durationInFrames: 450 },
  race: { from: 1950, durationInFrames: 540 },
  close: { from: 2490, durationInFrames: 210 },
} as const;

export const TOTAL_FRAMES = 2700;
