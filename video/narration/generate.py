"""Render the walkthrough narration with Chatterbox Turbo, one WAV per scene.

Each clip must fit its scene window; the script fails loudly on overflow so a
too-long line is rewritten rather than silently colliding with the next scene.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    import torch
    import torchaudio

    from chatterbox.tts_turbo import ChatterboxTurboTTS

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = ChatterboxTurboTTS.from_pretrained(device=device)

    plan = json.loads((HERE / "script.json").read_text())
    failures = []
    for line in plan["lines"]:
        out = HERE / f"{line['id']}.wav"
        wav = model.generate(line["text"]).cpu()
        # PCM16: the composition is rendered by a browser, and Python's own
        # wave module cannot even read the float WAVs torchaudio defaults to.
        torchaudio.save(str(out), wav, model.sr, encoding="PCM_S", bits_per_sample=16)
        duration = wav.shape[-1] / model.sr
        status = "OK " if duration <= line["max_s"] else "OVER"
        if duration > line["max_s"]:
            failures.append((line["id"], duration, line["max_s"]))
        print(f"{status} {line['id']:<8} {duration:5.2f}s (budget {line['max_s']:.1f}s)")

    if failures:
        print("\nover budget:", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
