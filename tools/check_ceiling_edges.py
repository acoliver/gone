"""Measure solid ceiling edges in the fixed 2304 x 1296 inspection cameras."""
import argparse
import json
from pathlib import Path

from PIL import Image

BAND = (0, 150, 2304, 480)
BLACK_LEVEL = 6
MAX_BLACK_FRACTION = 0.01
MAX_DARK_HALL_FRACTION = 0.10


def fractions(path):
    with Image.open(path) as image:
        if image.size != (2304, 1296):
            raise ValueError(f"Inspection capture must be 2304 x 1296: {path}")
        pixels = list(image.convert("RGB").crop(BAND).getdata())
    return {
        "black_fraction": sum(max(pixel) < BLACK_LEVEL for pixel in pixels) / len(pixels),
        "dark_fraction": sum(max(pixel) < 24 for pixel in pixels) / len(pixels),
    }


def check(directory):
    results = {}
    failures = []
    for circuit in ("secondary-white", "emergency"):
        for view in ("connector-bulkhead", "hall-end-wall"):
            name = f"{circuit}-{view}"
            result = fractions(directory / f"{name}.png")
            results[name] = result
            if result["black_fraction"] > MAX_BLACK_FRACTION:
                failures.append(f"{name}: black fraction {result['black_fraction']:.6f} > {MAX_BLACK_FRACTION}")
            if circuit == "secondary-white" and view == "hall-end-wall":
                if result["dark_fraction"] > MAX_DARK_HALL_FRACTION:
                    failures.append(f"{name}: dark fraction {result['dark_fraction']:.6f} > {MAX_DARK_HALL_FRACTION}")
    return results, failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    results, failures = check(args.directory)
    print(json.dumps({"views": results, "failures": failures}, indent=2))
    raise SystemExit(bool(failures))
