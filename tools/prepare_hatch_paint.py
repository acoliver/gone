#!/usr/bin/env python3
"""Pack generated, shadowless paint colour and derived paint height without tiling."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
# The wider, forward leaf from Andrew's 2026-11-05 design still needs one texel
# per production-camera pixel. These cells retain that density within 24 MB.
ATLAS_WIDTH = 1088
LEAF_WIDTH = ATLAS_WIDTH // 2
LEAF_HEIGHT = 1088
ATLAS_HEIGHT = 2048


def crop_resize(image, size):
    width, height = image.size
    ratio = size[0] / size[1]
    if width / height > ratio:
        crop_width = height * ratio
        box = ((width - crop_width) / 2, 0, (width + crop_width) / 2, height)
    else:
        crop_height = width / ratio
        box = (0, (height - crop_height) / 2, width, (height + crop_height) / 2)
    return image.resize(size, Image.Resampling.LANCZOS, box=box)


def paint_fields(image):
    colour = np.asarray(image.convert("RGB"), dtype=np.float32) / 255
    maximum, minimum = colour.max(2), colour.min(2)
    saturation = (maximum - minimum) / np.maximum(maximum, .001)
    # Green-grey sheets and red-brown substrate are separated by chroma, not
    # photographed illumination. Alpha stores the 1.5 mm raised paint layer.
    paint = np.clip((.48 - saturation) / .22, 0, 1)
    paint *= np.clip((colour[:, :, 1] / np.maximum(colour[:, :, 0], .001) - .48) / .24, 0, 1)
    paint = paint * paint * (3 - 2 * paint)
    return colour, paint


def calibrate_albedo(colour, gain):
    linear = np.where(colour <= .04045, colour / 12.92, ((colour + .055) / 1.055) ** 2.4)
    linear = np.clip(linear * np.asarray(gain), 0, 1)
    return np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)


def pack(front, back, frame, gains=None):
    atlas = np.zeros((ATLAS_HEIGHT, ATLAS_WIDTH, 4), dtype=np.uint8)
    fields = []
    cells = [(front, (0, 0, LEAF_WIDTH, LEAF_HEIGHT)),
             (back, (LEAF_WIDTH, 0, ATLAS_WIDTH, LEAF_HEIGHT)),
             (frame, (0, LEAF_HEIGHT, ATLAS_WIDTH, ATLAS_HEIGHT))]
    for index, (image, box) in enumerate(cells):
        x0, y0, x1, y1 = box
        colour, paint = paint_fields(crop_resize(image, (x1 - x0, y1 - y0)))
        if gains is not None:
            colour = calibrate_albedo(colour, gains[index])
        atlas[y0:y1, x0:x1, :3] = np.round(colour * 255).astype(np.uint8)
        atlas[y0:y1, x0:x1, 3] = np.round(paint * 255).astype(np.uint8)
        fields.append(paint)
    return Image.fromarray(atlas), fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "art-source/hatch")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/props/hatch")
    parser.add_argument("--parts", type=Path, help="fresh simulation export for physical map scale")
    args = parser.parse_args()
    images = [Image.open(args.source / (name + ".png")).convert("RGB") for name in ("leaf-front", "leaf-back", "frame")]
    calibration = json.loads((args.source / "albedo-calibration.json").read_text())["regions"]
    gains = [calibration[name]["linear_rgb_factor"] for name in ("leaf", "leaf", "frame")]
    atlas, _ = pack(*images, gains=gains)
    atlas.save(args.output / "hatch_painted.png")
    rgba = np.asarray(atlas, dtype=np.float32) / 255
    paint = rgba[:, :, 3]
    Image.fromarray(np.round(paint * 255).astype(np.uint8)).save(args.output / "paint_height.png")
    # Source normal is +Y OpenGL. Runtime differentiates the same height at
    # the physical leaf/frame projection, avoiding a second high-res sampler.
    document = json.loads((args.parts or args.output / "parts.json").read_text())
    plate = next(part for group in document["variants"][0]["groups"] for part in group["parts"]
                 if part["id"] == "ForeSteel/plate")
    density_x, density_y = LEAF_WIDTH / plate["size"][0], LEAF_HEIGHT / plate["size"][1]
    dy, dx = np.gradient(paint * .0015)
    normal = np.dstack((-dx * density_x, dy * density_y, np.ones_like(paint)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    Image.fromarray(np.round((normal * .5 + .5) * 255).astype(np.uint8)).save(args.output / "paint_normal.png")
    roughness = .91 * (1 - paint) + .69 * paint
    Image.fromarray(np.round(roughness * 255).astype(np.uint8)).save(args.output / "paint_roughness.png")
    print(json.dumps({"atlas": [ATLAS_WIDTH, ATLAS_HEIGHT],
                      "leaf_faces": [[0, 0, LEAF_WIDTH, LEAF_HEIGHT], [LEAF_WIDTH, 0, ATLAS_WIDTH, LEAF_HEIGHT]],
                      "frame": [0, LEAF_HEIGHT, ATLAS_WIDTH, ATLAS_HEIGHT], "paint_height_m": .0015,
                      "leaf_texels_per_metre": min(density_x, density_y)}))


if __name__ == "__main__":
    main()
