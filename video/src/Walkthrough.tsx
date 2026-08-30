/**
 * The 90-second walkthrough.
 *
 * Scenes are laid out on an absolute frame timeline from `SCENES` so a change
 * to one scene's length cannot silently shift the ones after it.
 */

import { AbsoluteFill, Sequence } from "remotion";
import { loadFont as loadBarlow } from "@remotion/google-fonts/Barlow";
import { loadFont as loadBarlowCondensed } from "@remotion/google-fonts/BarlowCondensed";
import { loadFont as loadPlexMono } from "@remotion/google-fonts/IBMPlexMono";

import {
  BoardScene,
  CloseScene,
  FactsScene,
  LedgerScene,
  RaceScene,
  TitleScene,
  UnknownScene,
} from "./scenes";
import { SCENES, theme } from "./theme";

loadBarlow();
loadBarlowCondensed();
loadPlexMono();

const TIMELINE = [
  { key: "title", scene: <TitleScene /> },
  { key: "board", scene: <BoardScene /> },
  { key: "facts", scene: <FactsScene /> },
  { key: "ledger", scene: <LedgerScene /> },
  { key: "unknown", scene: <UnknownScene /> },
  { key: "race", scene: <RaceScene /> },
  { key: "close", scene: <CloseScene /> },
] as const;

export function Walkthrough() {
  return (
    <AbsoluteFill style={{ background: theme.ground }}>
      {TIMELINE.map(({ key, scene }) => (
        <Sequence key={key} name={key} {...SCENES[key]}>
          {scene}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
