import { Composition } from "remotion";

import { Walkthrough } from "./Walkthrough";
import { FPS, TOTAL_FRAMES } from "./theme";

export function RemotionRoot() {
  return (
    <Composition
      id="Walkthrough"
      component={Walkthrough}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
  );
}
