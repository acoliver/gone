#!/usr/bin/env python3
"""Original hatch effects: seeded friction, impacts and inharmonic resonances.

Python standard library only. No recordings or model-generated material.
Recipe v1 uses xorshift32, fixed sample counts, and explicit little-endian PCM.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import wave

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/audio/hatch"
RATE = 48000
VERSION = "hatch-procedural-v1"
PEAK = 10 ** (-3 / 20)
# File, family, xorshift32 seed, sample count. Order is part of the recipe.
RECIPES = (
    ("grind-01.wav", "grind", 0x61C4A901, 43200),
    ("grind-02.wav", "grind", 0x61C4A902, 48000),
    ("grind-03.wav", "grind", 0x61C4A903, 46080),
    ("grind-04.wav", "grind", 0x61C4A904, 49920),
    ("stall-01.wav", "stall", 0x2D381001, 26400),
    ("stall-02.wav", "stall", 0x2D381002, 29760),
    ("stall-03.wav", "stall", 0x2D381003, 27840),
    ("wheel-refused-01.wav", "wheel-refused", 0x73A20F01, 34560),
    ("thud-01.wav", "thud", 0x9F121A01, 30720),
    ("thud-02.wav", "thud", 0x9F121A02, 36480),
    ("release-01.wav", "release", 0x8B431D01, 88800),
)


class Noise:
    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF or 0x6D2B79F5

    def draw(self) -> float:
        value = self.state
        value ^= (value << 13) & 0xFFFFFFFF
        value ^= value >> 17
        value ^= (value << 5) & 0xFFFFFFFF
        self.state = value & 0xFFFFFFFF
        return self.state / 2147483648.0 - 1.0


def finish(samples: list[float]) -> list[int]:
    """Fade, remove DC through the same window, and peak-normalize once."""
    if not samples or not all(math.isfinite(value) for value in samples):
        raise ValueError("expected finite, non-empty mono samples")
    count = len(samples)
    fade_in, fade_out = RATE * .008, RATE * .035
    window = [min(1., i / fade_in, (count - 1 - i) / fade_out) for i in range(count)]
    weighted = [sample * gain for sample, gain in zip(samples, window)]
    weight = sum(window)
    if not weight:
        raise ValueError("audio too short for fades")
    dc = sum(weighted) / weight
    centered = [sample - dc * gain for sample, gain in zip(weighted, window)]
    peak = max(abs(value) for value in centered)
    if peak == 0:
        raise ValueError("silent audio")
    scale = 32767 * PEAK / peak
    return [round(value * scale) for value in centered]


def wav_bytes(pcm: list[int]) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    return output.getvalue()


def synthesize(recipe: tuple[str, str, int, int]) -> bytes:
    _name, family, seed, count = recipe
    if family not in {"grind", "stall", "wheel-refused", "thud", "release"}:
        raise ValueError(f"unknown sound family: {family}")
    rng = Noise(seed)
    # A door plate's modes are deliberately inharmonic, with per-casting detune.
    frequencies = (171., 293., 487., 823., 1367., 2213.)
    if family == "thud":
        frequencies = (73., 121., 193., 317., 563., 947.)
    elif family == "release":
        frequencies = (89., 157., 271., 619., 1171., 1867.)
    modes = []
    for index, frequency in enumerate(frequencies):
        hz = frequency * (1 + .065 * rng.draw())
        decay = (.16 + .30 / (index + 1)) if family != "release" else (.28 + .85 / (index + 1))
        radius = math.exp(-1 / (RATE * decay))
        modes.append([2 * radius * math.cos(math.tau * hz / RATE), radius * radius, math.sin(math.tau * hz / RATE), 0., 0.])
    duration = count / RATE
    low = 0.
    previous = 0.
    samples = []
    for index in range(count):
        t = index / RATE
        noise = rng.draw()
        low += .14 * (noise - low)
        scrape = low - previous
        previous = low
        if family == "grind":
            # Irregular stick/slip bursts under continuing hand pressure.
            pressure = math.sin(math.pi * min(t / (duration * .85), 1.)) ** .7
            slip = max(0., math.sin(math.tau * (12 * t + 7 * t * t)) + .32 * noise)
            excitation = scrape * pressure * (.18 + slip)
            impact = .9 * math.exp(-t * 85) * noise
            excitation += impact
            dry = excitation * .7
        else:
            decay = 34 if family == "thud" else 48
            impact = noise * math.exp(-t * decay)
            # Secondary lug hits/rattle follow the initial strained clunk.
            for hit, gain in ((.075, .38), (.141, .20), (.237, .12)):
                if t >= hit:
                    impact += noise * gain * math.exp(-(t - hit) * 100)
            if family == "release":
                for hit, gain in ((.32, .85), (.67, .42)):
                    if t >= hit:
                        impact += noise * gain * math.exp(-(t - hit) * 55)
            strain = max(0., 1 - t / .22) * scrape * .22 if family in {"stall", "wheel-refused"} else 0.
            excitation = impact + strain
            dry = low * math.exp(-t * 24) * .9 if family == "thud" else excitation * .25
        resonant = 0.
        for mode in modes:
            a, b, drive, y1, y2 = mode
            value = a * y1 - b * y2 + drive * excitation
            mode[3], mode[4] = value, y1
            resonant += value
        samples.append(dry + resonant * .28)
    return wav_bytes(finish(samples))


def render_assets() -> dict[str, bytes]:
    return {recipe[0]: synthesize(recipe) for recipe in RECIPES}


def manifest(assets: dict[str, bytes]) -> dict:
    return {"version": VERSION, "prng": "xorshift32", "sample_rate": RATE,
            "channels": 1, "format": "PCM16LE", "peak_dbfs": -3,
            "files": [{"file": name, "family": family, "seed": seed, "frames": count,
                       "sha256": hashlib.sha256(assets[name]).hexdigest()}
                      for name, family, seed, count in RECIPES]}


def write_assets(output: Path, assets: dict[str, bytes]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, data in assets.items():
        (output / name).write_bytes(data)
    (output / "manifest.json").write_text(json.dumps(manifest(assets), indent=2) + "\n")


def check_assets(output: Path) -> None:
    assets = render_assets()
    for name, data in assets.items():
        if (output / name).read_bytes() != data:
            raise ValueError(f"generated audio differs: {name}")
    if json.loads((output / "manifest.json").read_text()) != manifest(assets):
        raise ValueError("generated audio manifest differs")


def write_audition(output: Path, assets: dict[str, bytes]) -> None:
    write_assets(output, assets)
    demo = [0] * (20 * RATE)
    # Eight hand presses (six turns/two stalls), release, two won't-budge tries.
    sequence = ((.5, "grind-01.wav", 1.24), (1.9, "grind-02.wav", 1.08),
                (3.3, "stall-01.wav", 1.), (4.7, "grind-03.wav", 1.33),
                (6.1, "grind-04.wav", .92), (7.5, "stall-03.wav", 1.),
                (8.9, "grind-01.wav", 1.16), (10.3, "grind-02.wav", .84),
                (10.4, "release-01.wav", 1.), (15., "wheel-refused-01.wav", 1.),
                (17., "thud-02.wav", 1.))
    for start, name, pitch in sequence:
        with wave.open(io.BytesIO(assets[name]), "rb") as wav:
            count = wav.getnframes()
            pcm = struct.unpack(f"<{count}h", wav.readframes(count))
        for index in range(int((len(pcm) - 1) / pitch)):
            source = index * pitch
            left = int(source)
            value = pcm[left] + (pcm[left + 1] - pcm[left]) * (source - left)
            demo[round(start * RATE) + index] += round(value * .8)
    (output / "demo-20s.wav").write_bytes(wav_bytes(demo))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare generated bytes to tracked assets without writing")
    parser.add_argument("--audition", type=Path, help="also copy the effects and a 20-second crank demo here")
    args = parser.parse_args()
    if args.check:
        if args.audition:
            parser.error("--check never writes; use --audition separately")
        check_assets(OUTPUT)
        print("PASS hatch audio: all 11 WAVs and manifest match")
    else:
        assets = render_assets()
        write_assets(OUTPUT, assets)
        if args.audition:
            write_audition(args.audition, assets)
        print(f"Wrote {len(assets)} original hatch effects to {OUTPUT}")


if __name__ == "__main__":
    main()
