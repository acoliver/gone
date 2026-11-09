"""Measure matched real-bounce captures and write a labelled contact sheet.

Requires Pillow and NumPy. Run with the directory containing base/, sdfgi/ and ssil/.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WEIGHTS = np.array([0.2126, 0.7152, 0.0722])
REGIONS = {
    "connector-bulkhead": [("rib-front", (1230, 390, 1340, 417), (1230, 338, 1340, 365))],
    "along-connector": [("far-rib-front", (1040, 578, 1080, 582), (1040, 540, 1080, 544))],
    "duct-collar-2m-connector-side": [
        ("left-duct-end", (396, 502, 416, 516), (396, 470, 416, 484)),
        ("right-duct-end", (1892, 502, 1912, 516), (1892, 470, 1912, 484)),
    ],
}


def crop_mean(luma, box):
    x0, y0, x1, y1 = box
    return float(luma[y0:y1, x0:x1].mean())


def analyze(directory):
    modes = ("base", "sdfgi", "ssil")
    records = {mode: json.loads((directory / mode / "captures.json").read_text()) for mode in modes}
    baseline = records["base"]
    results = {}
    sheet = Image.new("RGB", (2304, len(baseline) * 470 + 60), "#161616")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    draw.text((16, 14), "Actual fixture sources only. No ambient or energy boost. Displayed images, not exposure-normalized.", font=font)
    for row, record in enumerate(baseline):
        name = Path(record["path"]).name
        circuit = record["circuit"]
        view = name.removeprefix(circuit + "-").removesuffix(".png")
        results[name] = {}
        mask_path = directory / "base" / (view + ".mask.png")
        mask = None
        if mask_path.exists():
            with Image.open(mask_path) as image:
                mask = np.asarray(image.convert("L").filter(ImageFilter.MinFilter(3))) > 250
            if not mask.any():
                raise ValueError(f"Empty broad-shell mask: {mask_path}")
        for column, mode in enumerate(modes):
            other = records[mode][row]
            for key in ("owner", "circuit", "eye", "camera_transform", "fov", "snapshot"):
                assert other[key] == record[key], (mode, name, key)
            assert Path(other["path"]).name == name
            with Image.open(directory / mode / name) as source:
                assert source.size == (2304, 1296)
                rgb = np.asarray(source.convert("RGB"), dtype=np.float64) / 255
                thumb = source.convert("RGB").resize((768, 432))
            luma = rgb @ WEIGHTS
            linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4) @ WEIGHTS
            measured = {"display_mean": float(luma.mean()), "linear_mean": float(linear.mean()), "regions": {}}
            for label, box, adjacent in REGIONS.get(view, []):
                face = crop_mean(luma, box)
                neighbor = crop_mean(luma, adjacent)
                ratio = face / neighbor if neighbor else None
                measured["regions"][label] = {"face": face, "neighbor": neighbor, "ratio": ratio, "passes_0_30": ratio is not None and ratio >= 0.30}
            if mask is not None:
                measured["broad_shell"] = {"pixels": int(mask.sum()), "display_mean": float(luma[mask].mean()), "linear_mean": float(linear[mask].mean())}
            results[name][mode] = measured
            if mode != "base":
                for key in ("display_mean", "linear_mean"):
                    measured[key + "_change_percent"] = 100 * (measured[key] / results[name]["base"][key] - 1)
            x, y = column * 768, 60 + row * 470
            text = f"{mode}: {circuit} / {view}"
            draw.text((x + 8, y + 5), text, font=font, fill="white")
            sheet.paste(thumb, (x, y + 35))
    (directory / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    sheet.save(directory / "compare.jpg", quality=86)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    analyze(parser.parse_args().directory)
