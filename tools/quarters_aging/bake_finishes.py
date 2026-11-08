"""Derive two steel atlas sets from the shared quarters geometry masks.

Use the local Hunyuan Python (NumPy, Pillow and SciPy). Geometry fields are
baker intermediates; only PNG atlases and the mask/finish JSON ship at runtime.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt


def noise(points, frequency, seed):
    p = points * frequency
    grid = np.floor(p)
    blend = p - grid
    blend = blend * blend * (3 - 2 * blend)
    value = np.zeros(points.shape[:-1], np.float32)
    for x in (0, 1):
        for y in (0, 1):
            for z in (0, 1):
                dot = ((grid + [x, y, z]) * [127.1, 311.7, 74.7]).sum(-1) + seed * .13
                sample = np.mod(np.sin(dot) * 43758.5453, 1)
                weight = (blend[..., 0] if x else 1 - blend[..., 0])
                weight = weight * (blend[..., 1] if y else 1 - blend[..., 1])
                weight = weight * (blend[..., 2] if z else 1 - blend[..., 2])
                value += sample * weight
    return value


def write_atlas(path, data, nearest):
    data = data[tuple(nearest)]
    Image.fromarray(np.uint8(np.round(np.clip(data, 0, 1) * 255))).save(path)


def bake(directory, fields):
    metadata = json.loads((directory / "masks.json").read_text())
    geometry = np.asarray(Image.open(directory / "geometry_masks.png"), np.float32) / 255
    weather = np.asarray(Image.open(directory / "weather_masks.png"), np.float32) / 255
    arrays = np.load(fields)
    positions, occupied, ownership = arrays["position"], arrays["occupied"], arrays["ownership"]
    seed = metadata["seed"]
    coarse = noise(positions, 17, seed)
    flakes = noise(positions, 84, seed + 1)
    grain = noise(positions, 430, seed + 2)
    score = coarse * .66 + flakes * .34 + geometry[..., 2] * .23 + weather[..., 2] * .12
    corrosion = np.clip((score - .57) * 45 + .5, 0, 1)
    corrosion = np.maximum(corrosion, np.clip(weather[..., 1] * 1.65, 0, 1))
    corrosion = np.where(ownership == 2, .85 + grain * .15, corrosion)
    corrosion = np.where(ownership == 3, corrosion * .8, corrosion)
    dust = np.clip(weather[..., 0] * 2.5, 0, .93) * (.94 + grain * .06)
    paint = np.array([.473, .575, .556], np.float32)
    steel = np.array([.56, .59, .59], np.float32)
    dark = np.array([.23, .265, .26], np.float32)
    base = np.where((ownership == 1)[..., None], paint, np.where((ownership == 2)[..., None], steel, dark))
    nearest = distance_transform_edt(~occupied, return_distances=False, return_indices=True)
    ao = geometry[..., 0]
    for state in ("as_built", "aged"):
        rust = corrosion if state == "aged" else np.zeros_like(corrosion)
        powder = dust if state == "aged" else np.zeros_like(dust)
        rust_colour = np.stack([.37 + grain * .16, .135 + grain * .09, .042 + grain * .035], -1)
        colour = base * (1 if state == "as_built" else (.92 + flakes[..., None] * .08))
        colour = colour * (1 - rust[..., None]) + rust_colour * rust[..., None]
        colour = colour * (1 - powder[..., None]) + np.array([.47, .445, .40]) * powder[..., None]
        roughness = np.where(ownership == 2, .27, np.where(ownership == 1, .48, .52))
        roughness = roughness * (1 - rust) + (.89 + grain * .08) * rust
        roughness = roughness * (1 - powder) + .98 * powder
        metallic = np.where(ownership == 1, .02, .85) * (1 - rust) * (1 - powder)
        height = -rust * (.0003 + grain * .0007) + powder * .0002
        if state == "aged":
            height += (ownership == 1) * (1 - rust) * .0006
        # Differentiate padded height in atlas space, in metres, as hatch paint does.
        height = height[tuple(nearest)]
        dy, dx = np.gradient(height)
        density = metadata["texels_per_metre"]
        normals = np.stack([-dx * density, dy * density, np.ones_like(dx)], -1)
        normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
        write_atlas(directory / f"{state}_albedo.png", np.dstack([colour, rust]), nearest)
        write_atlas(directory / f"{state}_normal.png", np.dstack([normals * .5 + .5, np.ones_like(dx)]), nearest)
        write_atlas(directory / f"{state}_orm.png", np.stack([ao, roughness, metallic, powder], -1), nearest)
    metadata = {"method": "two baked atlas sets; shared geometry and masks; unchanged hatch shader",
                "age_years": {"as_built": 0, "aged": 1000}, "seed": seed,
                "as_built_paint_srgb": paint.tolist(),
                "channels": {"*_albedo.png": "RGB sRGB reflectance, A oxide coverage",
                             "*_normal.png": "RGB OpenGL tangent normal, A=1",
                             "*_orm.png": "R ambient occlusion, G roughness, B metallic, A dust coverage"},
                "detail_scans": "shared CC0 hatch_detail_steel/paint/oxide scans at 0.20 m pitch"}
    (directory / "finishes.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Baked both steel finishes", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--fields", type=Path, required=True)
    args = parser.parse_args()
    bake(args.directory, args.fields)


if __name__ == "__main__":
    main()
