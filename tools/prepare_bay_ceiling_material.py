#!/usr/bin/env python3
"""Bake source-colour ceiling paint and geometry-masked weathering for Godot."""
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "art-source/bay-ceiling"
OUT = ROOT / "assets/props/bay-ceiling/materials"
GUIDE = ART / "source-guide.json"
WIDTH_M, HEIGHT_M = 1.18, 0.58
WIDTH, HEIGHT = 2048, 1024

sys.path.insert(0, str(ROOT / "tools/blender"))
from bay_ceiling_geometry import FittedGuides


def linearize(rgb):
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def srgb(linear):
    linear = np.clip(linear, 0, 1)
    return np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)


def image_points(loop):
    return [((x / WIDTH_M + .5) * WIDTH, (1 - (y / HEIGHT_M + .5)) * HEIGHT) for x, y in loop]


def edge_distance(loops):
    lines = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(lines)
    for loop in loops:
        draw.line(image_points(loop) + [image_points(loop)[0]], fill=255, width=1)
    pixels_per_metre = (WIDTH / WIDTH_M, HEIGHT / HEIGHT_M)
    return distance_transform_edt(np.asarray(lines) == 0, sampling=(1 / pixels_per_metre[1], 1 / pixels_per_metre[0]))


def polygon_inside(outer, slots):
    image = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(image)
    draw.polygon(image_points(outer), fill=255)
    for slot in slots:
        draw.polygon(image_points(slot), fill=0)
    return np.asarray(image) > 0


def load_source(path):
    image = Image.open(path).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return linearize(np.asarray(image, dtype=np.float32) / 255)


def save_rgb(path, rgb):
    Image.fromarray(np.round(srgb(rgb) * 255).astype(np.uint8), "RGB").save(path)


# Damage locations bias cluster density, never fill whole patches with oxide.
WEAR_FIELDS = {
    "intact": (),
    "subtlewarp": ((.35, .16, .13, .07, .55),),
    "sag": ((-.18, -.03, .23, .17, .86), (-.12, .17, .075, .09, .65)),
    "torncorner": ((.22, .09, .25, .17, .92),),
    "brokenedge": ((-.26, -.09, .22, .145, .90), (-.40, .13, .12, .10, .68)),
}


def authored_wear(name):
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    x = (xx / WIDTH - .5) * WIDTH_M
    y = (.5 - yy / HEIGHT) * HEIGHT_M
    peel = np.zeros((HEIGHT, WIDTH))
    grime = np.zeros_like(peel)
    for cx, cy, rx, ry, strength in WEAR_FIELDS[name]:
        bent_x = x - cx + .12 * (y - cy)
        radius = np.sqrt((bent_x / rx) ** 2 + ((y - cy) / ry) ** 2)
        patch = np.exp(-radius ** 2 * 2)
        peel = np.maximum(peel, patch * strength)
        leak = np.exp(-((bent_x / (rx * .38)) ** 2 + ((y - cy + .045) / (ry * 1.6)) ** 2) * 2)
        grime = np.maximum(grime, leak * .32)
    return peel, grime


def millimetre_blur(field, millimetres):
    return gaussian_filter(field, (millimetres * HEIGHT / HEIGHT_M / 1000,
                                   millimetres * WIDTH / WIDTH_M / 1000))


@lru_cache(maxsize=2)
def source_structure(width, height):
    source = np.asarray(Image.open(ART / "generated-aged-steel-swatch.png").convert("RGB")
                        .resize((width, height), Image.Resampling.LANCZOS), dtype=np.float32) / 255
    luminance = source @ np.asarray([.2126, .7152, .0722])
    chroma = source[..., 0] - source[..., 2]
    # Remove broad illumination while retaining the source's pits and oxide islands.
    local_luma = millimetre_blur(luminance, .45) - millimetre_blur(luminance, 12)
    local_chroma = millimetre_blur(chroma, .65) - millimetre_blur(chroma, 24)
    dy, dx = np.gradient(millimetre_blur(luminance, .55))
    edges = np.hypot(dx, dy)
    score = (-.45 * local_luma / local_luma.std()
             + .40 * local_chroma / local_chroma.std()
             + .15 * (edges - edges.mean()) / edges.std())
    quantiles = np.quantile(score, np.linspace(0, 1, 1025))
    rank = np.interp(score, quantiles, np.linspace(0, 1, 1025))
    mottle = millimetre_blur(chroma, 3) - millimetre_blur(chroma, 15)
    mottle /= mottle.std()
    return rank, np.clip(mottle, -2, 2)


def corrosion_clusters(name):
    rank, mottle = source_structure(WIDTH, HEIGHT)
    # Mirrors keep colour and mask registered without repeated tiles or wrap seams.
    if name in ("subtlewarp", "torncorner"):
        rank, mottle = rank[:, ::-1], mottle[:, ::-1]
    if name in ("sag", "brokenedge"):
        rank, mottle = rank[::-1], mottle[::-1]
    peel, leak = authored_wear(name)
    density = {"intact": .075, "subtlewarp": .075, "sag": .13,
               "torncorner": .13, "brokenedge": .13}[name]
    broad = millimetre_blur(mottle, 25)
    broad = np.clip(broad / broad.std(), -1.5, 1.5)
    density = np.clip(density + .40 * peel + .12 * leak + .025 * mottle + .035 * broad, 0, .62)
    clusters = np.clip((rank - (1 - density)) / .055, 0, 1) * .90
    return clusters, mottle


def variant_masks(fit, name, slot_distance, variation, dust_field):
    outer = fit.damaged_outer(name)
    coverage = polygon_inside(outer, fit.slots)
    out_distance = edge_distance([outer])
    distance = np.minimum(out_distance, slot_distance)
    clusters, _ = corrosion_clusters(name)
    oxide = np.maximum(np.exp(-np.square(out_distance / .014)) * .76,
                       np.exp(-np.square(slot_distance / .006)) * .70) * variation
    oxide *= .58 + .42 * clusters / .90
    oxide = np.maximum(oxide, clusters) * coverage
    lip = np.exp(-np.square(distance / .0022)) * coverage
    dust = np.clip(np.exp(-np.square(distance / .012)) *
                   (0.025 + np.maximum(dust_field, 0) * .018), 0, .07) * coverage
    return coverage, oxide, lip, dust


def relief_maps(oxide, lip, dust, dust_field, height_scale=1.0):
    roughness = np.clip(.86 - oxide * .045 - lip * .07 + np.clip(dust_field, -1, 1) * .012, .75, .90)
    height_m = ((lip * .00022 + dust * .000045 + oxide * .00016) * height_scale).astype(np.float32)
    d_y, d_x = np.gradient(height_m, HEIGHT_M / HEIGHT, WIDTH_M / WIDTH)
    # Image rows descend as UV +V rises, matching prepare_hatch_paint.py's OpenGL bake.
    normal = np.dstack((-d_x, d_y, np.ones_like(height_m)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    return roughness, height_m, normal


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fit = FittedGuides(json.loads(GUIDE.read_text()))
    geometry_path = ROOT / "assets/props/bay-ceiling/manifest.json"
    manifest = json.loads(geometry_path.read_text())
    assert len(fit.slots) == manifest["slot_count"] == 28
    assert np.array_equal(fit.outer, np.asarray(manifest["fit"]["outer_blender_xy_m"]))
    assert np.array_equal(fit.inner, np.asarray(manifest["fit"]["inner_blender_xy_m"]))
    slots = fit.slots
    base = load_source(ART / "generated-charcoal-paint-swatch.png")
    oxide_source = load_source(ART / "generated-aged-steel-swatch.png")
    _, dust_field = source_structure(WIDTH, HEIGHT)
    slot_distance = edge_distance(slots)
    variation = np.clip(.78 + .07 * dust_field, .48, 1.0)
    base *= np.asarray([1.08, 1.04, 1.00], dtype=np.float32)  # linear-light charcoal calibration
    base = np.clip(base, 0, 1)
    # Pale paint lips and dust are sampled from the high end of the approved base swatch.
    source_highlight = np.clip(base * np.asarray([1.40, 1.34, 1.20]), 0, 1)
    oxide_rgb = oxide_source * np.asarray([.88, .82, .76])
    base_luminance = np.sum(base * np.asarray([.2126, .7152, .0722]), axis=2)
    oxide_luminance = np.sum(oxide_rgb * np.asarray([.2126, .7152, .0722]), axis=2)
    # A single gain retains source contrast. Per-pixel luminance matching erased it.
    oxide_gain = float(np.median(base_luminance) * .95 / np.median(oxide_luminance))
    oxide_rgb = np.clip((oxide_luminance[..., None] + .55 *
                         (oxide_rgb - oxide_luminance[..., None])) * oxide_gain, 0, 1)
    broad_steel = millimetre_blur(oxide_luminance, 35)
    broad_steel = np.clip(broad_steel / np.median(broad_steel), .3, 1.6)
    weathered_base = base * (.30 + .70 * broad_steel[..., None])

    save_rgb(OUT / "control_albedo.png", base)
    Image.new("L", (WIDTH, HEIGHT), round(.86 * 255)).save(OUT / "control_roughness.png")
    Image.new("RGB", (WIDTH, HEIGHT), (128, 128, 255)).save(OUT / "control_normal.png")
    variants = {}
    for name in ("intact", "subtlewarp", "sag", "torncorner", "brokenedge"):
        outer = fit.damaged_outer(name)
        np.testing.assert_array_equal(outer, manifest["variants"][name]["outer_blender_xy_m"])
        coverage, variant_oxide, lip, dust = variant_masks(fit, name, slot_distance, variation, dust_field)
        calibrated_base = weathered_base
        calibrated_oxide = oxide_rgb
        if name in ("subtlewarp", "torncorner"):
            calibrated_oxide = calibrated_oxide[:, ::-1]
            calibrated_base = calibrated_base[:, ::-1]
        if name in ("sag", "brokenedge"):
            calibrated_oxide = calibrated_oxide[::-1]
            calibrated_base = calibrated_base[::-1]
        albedo = np.clip(calibrated_base * (1 - lip[..., None] * .46 - dust[..., None]), 0, 1)
        albedo = albedo * (1 - variant_oxide[..., None]) + calibrated_oxide * variant_oxide[..., None]
        albedo = albedo * (1 - lip[..., None] * .62) + source_highlight * (lip[..., None] * .62)
        albedo = albedo * (1 - dust[..., None]) + source_highlight * dust[..., None]
        # UVs are planar across the complete panel. Preserve readable source colour
        # outside the mesh because transparent borders are unnecessary for opaque PBR.
        save_rgb(OUT / f"{name}_albedo.png", albedo)
        roughness, height_m, normal = relief_maps(variant_oxide, lip, dust, dust_field, height_scale=.24)
        rough_image = Image.fromarray(np.round(roughness * 255).astype(np.uint8), "L")
        normal_image = Image.fromarray(np.round((normal * .5 + .5) * 255).astype(np.uint8), "RGB")
        rough_image.save(OUT / f"{name}_roughness.png")
        normal_image.save(OUT / f"{name}_normal.png")
        if name == "intact":
            rough_image.save(OUT / "roughness.png")
            normal_image.save(OUT / "normal.png")
        variants[name] = {
            "oxide_coverage_percent_of_panel": round(float(np.mean(variant_oxide[coverage] > .12) * 100), 2),
            "paint_visible_percent_of_panel": round(float(np.mean((variant_oxide[coverage] <= .12)) * 100), 2),
            "roughness_texture_range": [float(roughness.min()), float(roughness.max())],
            "paint_height_max_m": float(height_m.max()),
            "authored_fields_m": WEAR_FIELDS[name],
            "wear_vs_control_srgb_mean_abs_8bit": float(np.mean(np.abs(srgb(albedo)[coverage] - srgb(base)[coverage])) * 255),
            "wear_vs_control_srgb_p95_max_channel_8bit": float(np.percentile(np.max(np.abs(srgb(albedo) - srgb(base)), axis=2)[coverage], 95) * 255),
            "visible_contrast_pixels_percent_gt_8_levels": float(np.mean(np.max(np.abs(srgb(albedo) - srgb(base)), axis=2)[coverage] > 8 / 255) * 100),
            "files": [f"{name}_albedo.png", f"{name}_roughness.png", f"{name}_normal.png"],
        }

    oxide_percent = variants["intact"]["oxide_coverage_percent_of_panel"]
    report = {
        "uv": "UV0 broad faces: u=x/1.18+0.5, v=y/0.58+0.5; image rows vertically flipped. Return edges project bottom UVs 2 mm into the adjacent metal bank. Sloped rim uses planar projection; no extra atlas reservation.",
        "geometry_manifest_sha256": hashlib.sha256(geometry_path.read_bytes()).hexdigest(),
        "source_sha256": {name: hashlib.sha256((ART / name).read_bytes()).hexdigest() for name in
                          ("generated-charcoal-paint-swatch.png", "generated-aged-steel-swatch.png")},
        "binding_handoff": "BayCeilingMaterial binds all five matching map triplets. Shared roughness.png and normal.png alias intact. Control maps retain the same charcoal source with wear disabled.",
        "normal_convention": "OpenGL tangent XYZ=(-dheight/dcolumn,+dheight/drow,1), normalized; image rows descend as UV +V rises, matching tools/prepare_hatch_paint.py.",
        "wear_composition": "Source luminance, red-blue chroma and luminance edges select irregular corrosion clusters. Fine filters remain 0.45-0.65 mm; 25 mm source-derived density modulation creates quieter areas between clusters. Damage-location fields bias density only. A 35 mm low-pass of source steel luminance modulates broad paint value; it is not a solid oxide patch or a shadow. No synthetic colour noise, peel outline or baked directional grime. Mirrored source colours and masks remain registered. Geometry edges retain narrow wear. Production height scale 0.24 gives a maximum paint film below 90 micrometres; runtime normal scale remains 0.35.",
        "source_structure": {"fine_filter_sigma_mm": [.45, .65], "local_contrast_sigma_mm": [12, 24], "mottle_sigma_mm": [3, 15], "density_sigma_mm": 25, "broad_paint_value_sigma_mm": 35, "broad_paint_value_strength": .70, "target_pit_flake_mm": [1, 4], "target_mottle_mm": [10, 30], "oxide_single_linear_gain": oxide_gain, "oxide_linear_saturation": .55, "production_height_scale": .24},
        "dust_status": "Small existing edge contribution retained; dust visibility is not confirmed.",
        "resolution": [WIDTH, HEIGHT], "physical_coverage_m": [WIDTH_M, HEIGHT_M],
        "base_source": "art-source/bay-ceiling/generated-charcoal-paint-swatch.png",
        "localized_oxide_source": "art-source/bay-ceiling/generated-aged-steel-swatch.png",
        "mask_source": "outer/inner contours asserted byte-for-value against the geometry manifest; 28 fitted capsule slot contours reconstructed from tools/blender/bay_ceiling_geometry.py; coverage measured only on panel pixels outside slots",
        "shade": {"metallic": 0.22, "roughness_texture_range": [float(roughness.min()), float(roughness.max())], "paint_height_max_m": float(height_m.max()), "emission": 0.0},
        "oxide_coverage_percent": round(oxide_percent, 2), "paint_visible_percent": round(100 - oxide_percent, 2),
        "variants": variants,
        "files": ["*_albedo.png", "*_roughness.png", "*_normal.png", "roughness.png", "normal.png"],
        "calibration": "Sources converted sRGB->linear, channel calibrated, then encoded sRGB. Base gains (1.08,1.04,1.00); control maps unchanged. Oxide gains (0.88,0.82,0.76), linear saturation 0.55, and one global scalar matching median luminance to charcoal x0.95. No per-pixel luminance normalization. Broad paint value uses low-pass source steel luminance. Baseline single-input rendered ablations identify albedo/mask contrast as the dominant contributor, not roughness or normals; see tmp/verify-stasis-ceiling/material-balanced/baseline-ab/ab-measurements.json. Numerical evidence does not establish visual acceptance.",
        "texture_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(OUT.glob("*.png"))},
    }
    (OUT / "material-provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
