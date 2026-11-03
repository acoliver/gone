#!/usr/bin/env python3
"""Original ceiling ventilation hiss, synthesized from seeded filtered noise.

Standard library only, with the hatch generator's xorshift32 and PCM writer.
No recordings, samples or model-generated material.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from generate_hatch_audio import Noise, RATE, wav_bytes

OUTPUT = Path(__file__).resolve().parents[1] / "assets/audio/ventilation"
SEED = 0x71A1B4C2
FRAMES = 8 * RATE


def synthesize() -> bytes:
    noise = Noise(SEED)
    low = 0.0
    rumble = 0.0
    samples = []
    for index in range(FRAMES):
        t = index / RATE
        low += 0.16 * (noise.draw() - low)
        rumble += 0.008 * (low - rumble)
        envelope = min(1.0, t / 0.5, (8.0 - t) / 1.0)
        envelope = envelope * envelope * (3.0 - 2.0 * envelope)
        flutter = 0.92 + 0.08 * math.sin(math.tau * 0.7 * t)
        samples.append((low - rumble * 0.8) * envelope * flutter)
    scale = 32767 * 10 ** (-24 / 20) / max(abs(value) for value in samples)
    return wav_bytes([round(value * scale) for value in samples])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    audio = synthesize()
    manifest = {"version": "ventilation-procedural-v1", "prng": "xorshift32",
                "seed": SEED, "frames": FRAMES, "sample_rate": RATE,
                "channels": 1, "format": "PCM16LE", "peak_dbfs": -24,
                "file": "ceiling-clear.wav", "sha256": hashlib.sha256(audio).hexdigest()}
    if args.check:
        assert (OUTPUT / manifest["file"]).read_bytes() == audio, "vent audio differs"
        assert json.loads((OUTPUT / "manifest.json").read_text()) == manifest, "vent manifest differs"
        print("PASS ventilation audio: WAV and manifest match")
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / manifest["file"]).write_bytes(audio)
        (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(manifest["sha256"])


if __name__ == "__main__":
    main()
