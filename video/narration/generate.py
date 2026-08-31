"""Render the walkthrough narration with Chatterbox, one WAV per scene.

Voice: the non-Turbo Chatterbox default voice at exaggeration=0.75, cfg_weight=0.4,
temperature=0.85 -- the same config proven on the Archegos and School Buses films.
Chatterbox Turbo was tried here first and rejected: it silently ignores
exaggeration/cfg_weight (its own library warns about this) and reads flat.

Each clip must fit its scene window; the script fails loudly on overflow so a
too-long line is rewritten rather than silently colliding with the next scene.
Outputs land in both narration/ and public/vo/ so the render sees them directly.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC_VO = HERE.parent / "public" / "vo"

EXAGGERATION, CFG_WEIGHT, TEMPERATURE = 0.75, 0.4, 0.85


def main() -> int:
    import torch
    import torchaudio

    from chatterbox.tts import ChatterboxTTS

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = ChatterboxTTS.from_pretrained(device=device)

    PUBLIC_VO.mkdir(parents=True, exist_ok=True)
    plan = json.loads((HERE / "script.json").read_text())
    # Optional id filter so a single line can be re-rolled without disturbing
    # the takes already approved for the other scenes: `generate.py close`.
    only = set(sys.argv[1:])
    failures = []
    for line in plan["lines"]:
        if only and line["id"] not in only:
            continue
        out = HERE / f"{line['id']}.wav"
        wav = model.generate(
            line["text"],
            exaggeration=EXAGGERATION,
            cfg_weight=CFG_WEIGHT,
            temperature=TEMPERATURE,
        ).cpu()
        # PCM16: the composition is rendered by a browser, and Python's own
        # wave module cannot even read the float WAVs torchaudio defaults to.
        torchaudio.save(str(out), wav, model.sr, encoding="PCM_S", bits_per_sample=16)
        shutil.copyfile(out, PUBLIC_VO / out.name)
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
