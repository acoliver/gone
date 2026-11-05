"""Measured neutral-lookdev targets from the round-nine hatch brief.

Run after rendering: HATCH_NEUTRAL_IMAGE=... python tests/test_hatch_colour.py.
HSL of mean sRGB matches the brief; older HSV patch targets remain separate.
"""
import colorsys
import os
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REGIONS = {"leaf": (420, 560, 560, 900), "frame": (300, 300, 340, 700)}


def measure(image, box):
    srgb = np.asarray(image.crop(box).convert("RGB"), dtype=np.float64) / 255
    rgb = srgb.mean(axis=(0, 1))
    linear = np.where(srgb <= .04045, srgb / 12.92, ((srgb + .055) / 1.055) ** 2.4)
    hue, _, saturation = colorsys.rgb_to_hls(*rgb)
    return {"rgb": rgb * 255, "luminance": float((linear @ [.2126, .7152, .0722]).mean()),
            "hue": float(hue * 360), "saturation": float(saturation)}


class HatchColourTest(unittest.TestCase):
    def test_neutral_painted_leaf_and_frame_match_concept(self):
        path = os.environ.get("HATCH_NEUTRAL_IMAGE")
        if path is None:
            self.skipTest("requires a native neutral-lookdev capture")
        concept = Image.open(ROOT / "docs/art/corridors/hatch-concept-rusted.png")
        candidate = Image.open(path)
        for name, box in REGIONS.items():
            with self.subTest(region=name):
                expected, actual = measure(concept, box), measure(candidate, box)
                ratio = actual["luminance"] / expected["luminance"]
                hue_delta = abs((actual["hue"] - expected["hue"] + 180) % 360 - 180)
                sat_delta = abs(actual["saturation"] - expected["saturation"])
                print(f"HATCH_COLOUR {name} rgb={actual['rgb']} luminance_ratio={ratio:.6f} hue_delta={hue_delta:.6f} hsl_sat_delta={sat_delta:.6f}")
                # These boxes and tolerances are the owner's measured paint targets.
                self.assertLessEqual(abs(ratio - 1), .10, name + " linear luminance")
                self.assertLessEqual(hue_delta, 12, name + " hue")
                self.assertLessEqual(sat_delta, .10, name + " HSL saturation")


if __name__ == "__main__":
    unittest.main()
