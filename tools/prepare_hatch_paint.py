#!/usr/bin/env python3
"""Pack generated, shadowless paint colour and derived paint height without tiling."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


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


def pack(front, back, frame):
    atlas = np.zeros((2048, 1024, 4), dtype=np.uint8)
    fields = []
    for image, box in [(front, (0, 0, 512, 1088)), (back, (512, 0, 1024, 1088)), (frame, (0, 1088, 1024, 2048))]:
        x0, y0, x1, y1 = box
        colour, paint = paint_fields(crop_resize(image, (x1 - x0, y1 - y0)))
        atlas[y0:y1, x0:x1, :3] = np.round(colour * 255).astype(np.uint8)
        atlas[y0:y1, x0:x1, 3] = np.round(paint * 255).astype(np.uint8)
        fields.append(paint)
    return Image.fromarray(atlas), fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "art-source/hatch")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/props/hatch")
    args = parser.parse_args()
    images = [Image.open(args.source / (name + ".png")).convert("RGB") for name in ("leaf-front", "leaf-back", "frame")]
    atlas, _ = pack(*images)
    atlas.save(args.output / "hatch_painted.png")
    rgba = np.asarray(atlas, dtype=np.float32) / 255
    paint = rgba[:, :, 3]
    Image.fromarray(np.round(paint * 255).astype(np.uint8)).save(args.output / "paint_height.png")
    # Source normal is +Y OpenGL. Runtime differentiates the same height at
    # the physical leaf/frame projection, avoiding a second high-res sampler.
    document = json.loads((args.output / "parts.json").read_text())
    plate = next(part for group in document["variants"][0]["groups"] for part in group["parts"]
                 if part["id"] == "ForeSteel/plate")
    density_x, density_y = 512 / plate["size"][0], 1088 / plate["size"][1]
    dy, dx = np.gradient(paint * .0015)
    normal = np.dstack((-dx * density_x, dy * density_y, np.ones_like(paint)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    Image.fromarray(np.round((normal * .5 + .5) * 255).astype(np.uint8)).save(args.output / "paint_normal.png")
    roughness = .91 * (1 - paint) + .69 * paint
    Image.fromarray(np.round(roughness * 255).astype(np.uint8)).save(args.output / "paint_roughness.png")
    print(json.dumps({"atlas": [1024, 2048], "leaf_faces": [[0, 0, 512, 1088], [512, 0, 1024, 1088]], "frame": [0, 1088, 1024, 2048], "paint_height_m": .0015, "leaf_texels_per_metre": min(density_x, density_y)}))


if __name__ == "__main__":
    main()
