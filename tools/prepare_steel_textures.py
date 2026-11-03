"""Reproduce the three approved scan albedos without modifying captured renders.

Dependencies used for the approved images: see assets/surfaces/steel/SOURCES.md.
Originals live in art-source/steel (excluded from Godot import/export).
"""
from pathlib import Path
import argparse
import hashlib
import io

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "assets/surfaces/steel"
SETS = ("green_metal_rust", "rusty_painted_metal", "rusty_metal_04")
LUMA = np.array([0.2126, 0.7152, 0.0722])


def prepare(source: Path) -> bytes:
    srgb = np.asarray(Image.open(source).convert("RGB"), dtype=float) / 255
    rgb = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    lum = rgb @ LUMA
    broad = gaussian_filter(lum, 24, mode="wrap")
    detail = np.clip(lum / np.maximum(broad, 0.008), 0.72, 1.35)
    new_lum = 0.12 * detail ** 0.55 * (np.maximum(broad, 0.008) / np.median(broad)) ** 0.10
    chroma = rgb / np.maximum(lum[..., None], 0.004)
    smooth_chroma = gaussian_filter(chroma, (24, 24, 0), mode="wrap")
    new_chroma = np.array([1.35, 0.96, 0.60]) + 0.22 * (chroma - smooth_chroma)
    linear = np.clip(new_lum[..., None] * new_chroma, 0, 1)
    encoded = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    output = io.BytesIO()
    Image.fromarray(np.rint(encoded * 255).clip(0, 255).astype("uint8")).save(output, format="PNG")
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare without writing")
    args = parser.parse_args()
    for name in SETS:
        source = (ROOT / "art-source/steel") / f"{name}_albedo.jpg"
        target = RUNTIME / f"r4-{name}-albedo.png"
        data = prepare(source)
        if args.check:
            if target.read_bytes() != data:
                raise SystemExit(f"derived albedo mismatch: {target}")
        else:
            target.write_bytes(data)
        print(target.name, hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
