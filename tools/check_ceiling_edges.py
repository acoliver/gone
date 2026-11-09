"""Measure solid ceiling edges in the fixed 2304 x 1296 inspection cameras."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageStat

BAND = (0, 150, 2304, 480)
BLACK_LEVEL = 6
MAX_BLACK_FRACTION = 0.01
MAX_DARK_HALL_FRACTION = 0.10
MIN_LUMINANCE_RATIO = 0.30
# Closed duct ends and rib fronts identified by triangle rays at these cameras.
# Pair each face with the neighboring downward-facing sheet, not a light lens.
REGIONS = {
    "duct-collar-2m-connector-side": (
        ("left-duct-end", (396, 502, 416, 516), (396, 470, 416, 484)),
        ("right-duct-end", (1892, 502, 1912, 516), (1892, 470, 1912, 484)),
    ),
    "connector-bulkhead": (
        ("rib-front", (1230, 390, 1340, 417), (1230, 338, 1340, 365)),
    ),
    "along-connector": (
        ("far-rib-front", (1040, 578, 1080, 582), (1040, 540, 1080, 544)),
    ),
}


def region_measurements(path, regions):
    results = {}
    with Image.open(path) as source:
        image = source.convert("RGB")
        for name, box, adjacent in regions:
            face = ImageStat.Stat(image.crop(box)).mean
            ceiling = ImageStat.Stat(image.crop(adjacent)).mean
            luminance = sum(value * weight for value, weight in zip(face, (0.2126, 0.7152, 0.0722)))
            reference = sum(value * weight for value, weight in zip(ceiling, (0.2126, 0.7152, 0.0722)))
            results[name] = {
                "box": box, "adjacent": adjacent, "mean_rgb": face,
                "mean_luminance": luminance, "adjacent_luminance": reference,
                "luminance_ratio": luminance / reference if reference > 0 else 0.0,
            }
    return results


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
        for view in ("connector-bulkhead", "hall-end-wall", "duct-collar-2m-connector-side", "along-connector"):
            name = f"{circuit}-{view}"
            path = directory / f"{name}.png"
            result = fractions(path)
            results[name] = result
            if view in ("connector-bulkhead", "hall-end-wall") and result["black_fraction"] > MAX_BLACK_FRACTION:
                failures.append(f"{name}: black fraction {result['black_fraction']:.6f} > {MAX_BLACK_FRACTION}")
            if circuit == "secondary-white" and view == "hall-end-wall":
                if result["dark_fraction"] > MAX_DARK_HALL_FRACTION:
                    failures.append(f"{name}: dark fraction {result['dark_fraction']:.6f} > {MAX_DARK_HALL_FRACTION}")
            if view in REGIONS:
                result["regions"] = region_measurements(path, REGIONS[view])
                for region, measured in result["regions"].items():
                    if measured["luminance_ratio"] < MIN_LUMINANCE_RATIO:
                        failures.append(f"{name}: {region} luminance ratio {measured['luminance_ratio']:.6f} < {MIN_LUMINANCE_RATIO}")
    return results, failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    results, failures = check(args.directory)
    print(json.dumps({"views": results, "failures": failures}, indent=2))
    raise SystemExit(bool(failures))
