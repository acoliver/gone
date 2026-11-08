"""Measure actual Godot finish visibility, exported UVs and deterministic bakes.

The original hue/coverage gates remain unchanged. Matched neutral, present and
unlit controls also measure dust contrast, physical streak strips and edge
weighting. Atlas-only material and pitting checks are reported separately.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import label


def rgb(path):
    return np.asarray(Image.open(path).convert("RGB"), np.float32) / 255


def hsv(colour):
    maximum, minimum = colour.max(-1), colour.min(-1)
    delta = maximum - minimum
    saturation = delta / np.maximum(maximum, 1e-8)
    hue = np.zeros_like(maximum)
    for channel, offset in [(0, 0), (1, 2), (2, 4)]:
        selected = (colour.argmax(-1) == channel) & (delta > 1e-8)
        a, b = [(1, 2), (2, 0), (0, 1)][channel]
        hue[selected] = ((colour[..., a] - colour[..., b])[selected] / delta[selected] + offset) * 60
    return hue % 360, saturation, maximum


def rust_pixels(colour):
    hue, saturation, value = hsv(colour)
    return (hue >= 5) & (hue <= 45) & (saturation > .30) & (value > .10)


def newly_green(clean, aged, prop):
    def green(colour):
        hue, saturation, _ = hsv(colour)
        return (hue >= 70) & (hue <= 170) & (saturation > .25)
    new = green(aged) & ~green(clean) & prop
    components, count = label(new, np.ones((3, 3)))
    areas = np.bincount(components.ravel())[1:]
    largest = int(areas.max()) if count else 0
    return largest / max(1, int(prop.sum())), int(new.sum()) / max(1, int(prop.sum()))


def project(point, camera):
    position, target = np.array(camera["position"]), np.array(camera["target"])
    back = position - target
    back /= np.linalg.norm(back)
    right = np.cross([0, 1, 0], back)
    right /= np.linalg.norm(right)
    up = np.cross(back, right)
    delta = np.array(point) - target
    width, height = camera["image_size"]
    return np.array([width / 2 + np.dot(delta, right) * height / camera["size"],
                     height / 2 - np.dot(delta, up) * height / camera["size"]])


def streak_fraction(directory, preview, masks):
    ids = rgb(directory / "aged-ids-front.png")
    painted = (ids[..., 0] > .95) & (ids[..., 2] > .95)
    rust = rust_pixels(rgb(directory / "aged-albedo-front.png"))
    camera = preview["cameras"]["front"]
    results = []
    excluded = 0
    for source in masks["sources"]:
        if source["part"] not in ("Rivets", "Hinges"):
            continue
        x, y, z = source["position_blender"]
        # Probe the receiving surface beneath the physical fastener, not its cap.
        rows = []
        for drop in np.linspace(.018 if source["part"] == "Rivets" else .052, .10, 10):
            sx, sy = project([x, z - drop, -y], camera)
            cx, cy = int(round(sx)), int(round(sy))
            radius = max(1, int(round(.008 * 1024 / camera["size"])))
            if not (radius <= cx < 1024 - radius and 0 <= cy < 1024):
                continue
            region = painted[cy, cx - radius:cx + radius + 1]
            if region.any():
                rows.append(bool((rust[cy, cx - radius:cx + radius + 1] & region).any()))
        if len(rows) < 4:
            excluded += 1
            continue
        results.append({"source": source, "rusted_rows": sum(rows), "receiver_rows": len(rows), "streak": sum(rows) / len(rows) >= .70})
    if not results:
        raise ValueError("no measurable fasteners in capture")
    return sum(row["streak"] for row in results) / len(results), results, excluded


def measure(directory, mask_file):
    preview = json.loads((directory / "preview.json").read_text())
    masks = json.loads(mask_file.read_text())
    painted_count = aged_rust = clean_rust = 0
    new_green = []
    up_count = dust_count = 0
    for angle in ("hero", "front", "detail", "top"):
        clean = rgb(directory / f"as_built-albedo-{angle}.png")
        aged = rgb(directory / f"aged-albedo-{angle}.png")
        ids = rgb(directory / f"aged-ids-{angle}.png")
        prop = ids[..., 2] > .95
        painted = prop & (ids[..., 0] > .95)
        if angle in ("hero", "front"):
            painted_count += int(painted.sum())
            aged_rust += int((rust_pixels(aged) & painted).sum())
            clean_rust += int((rust_pixels(clean) & painted).sum())
        new_green.append(newly_green(clean, aged, prop))
        if angle == "top":
            up = prop & (ids[..., 1] > .95)
            h, s, v = hsv(aged)
            dust = (h >= 20) & (h <= 55) & (s >= .06) & (s <= .25) & (v > .25)
            dust &= np.linalg.norm(aged - clean, axis=-1) > .035
            up_count += int(up.sum())
            dust_count += int((up & dust).sum())
    if not painted_count or not up_count:
        raise ValueError("capture contains no measured painted or up-facing surfaces")
    streak, fasteners, excluded = streak_fraction(directory, preview, masks)
    values = {"aged_painted_rust": aged_rust / painted_count, "as_built_rust": clean_rust / painted_count,
              "fasteners_with_streaks": streak, "up_face_dust": dust_count / up_count,
              "new_green_largest_region": max(row[0] for row in new_green),
              "new_green_total": max(row[1] for row in new_green)}
    same = all(preview[name] for name in ("same_mesh", "same_pivots", "same_part_names", "same_footprint"))
    gates = {"aged_painted_rust": .25 <= values["aged_painted_rust"] <= .60,
             "as_built_rust": values["as_built_rust"] < .01,
             "fasteners_with_streaks": streak >= .80, "up_face_dust": values["up_face_dust"] >= .70,
             "no_new_green": values["new_green_total"] < .005, "identical_geometry": same}
    return {"passed": all(gates.values()), "values": values, "gates": gates,
            "thresholds": {"aged_painted_rust": [.25, .60], "as_built_rust": "<0.01",
                           "fasteners_with_streaks": ">=0.80", "up_face_dust": ">=0.70",
                           "new_green_total": "<0.005", "identical_geometry": True},
            "counts": {"painted_pixels": painted_count, "up_face_pixels": up_count,
                       "fasteners": len(fasteners), "fasteners_without_visible_receiver": excluded},
            "fasteners": fasteners}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--masks", type=Path, required=True)
    parser.add_argument("--fields", type=Path, required=True)
    parser.add_argument("--repeat", type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.captures, args.masks)
    from locker_visibility import measure_visibility
    extra = measure_visibility(args.captures, json.loads(args.masks.read_text()), json.loads((args.captures / 'preview.json').read_text()), args.masks.with_name('finishes.json'))
    from atlas_gates import uv_metrics, measure_atlases, repeat_metrics
    repeated = repeat_metrics(args.masks.parent, args.repeat)
    extra['values'].update(repeated)
    for name in ('byte_identical_bakes', 'byte_identical_export'):
        extra['gates'][name] = repeated[name]
        extra['thresholds'][name] = True
    uv = uv_metrics(args.masks.parent.with_suffix('.glb'))
    atlas = measure_atlases(args.masks.parent, args.fields)
    extra['values'].update(exported_uv_density_range=[uv['density_min'], uv['density_max']],
                           exported_uv_max_stretch=uv['max_stretch'], **atlas)
    extra['gates']['exported_uv_density'] = uv['density_min'] >= 304.6*.85 and uv['density_max'] <= 304.6*1.15
    extra['gates']['exported_uv_no_stretch'] = uv['max_stretch'] <= 1.015
    lo, hi = atlas['paint_roughness_range']
    extra['gates']['paint_roughness_range'] = .34 <= lo and hi <= .56 and hi-lo >= .12
    extra['gates']['bare_steel_pit_normal_rms'] = atlas['bare_steel_pit_normal_rms'] >= .01
    extra['gates']['hardware'] = all(row['rust_fraction'] >= .30 and row['pit_normal_rms'] >= .01 for row in atlas['hardware'].values())
    extra['thresholds']['hardware'] = 'each named hardware part: atlas rust>=0.30, pit normal RMS>=0.01'
    extra['values']['chroma_hardware_rust_min'] = min(row['chroma_rust_fraction'] for row in atlas['hardware'].values())
    extra['gates']['chroma_hardware_rust_min'] = extra['values']['chroma_hardware_rust_min'] >= .30
    extra['thresholds']['chroma_hardware_rust_min'] = '>=0.30 on each actual hardware mesh; hatch paint_fields rule'
    extra['thresholds'].update(exported_uv_density='304.6 +/-15% px/m, every triangle singular value',
                               exported_uv_no_stretch='anisotropy <=1.015, every triangle',
                               paint_roughness_range='about 0.35..0.55, span>=0.12',
                               bare_steel_pit_normal_rms='>=0.01 tangent-normal deviation')
    from locker_swatch_gates import measure_swatches
    swatches = measure_swatches(args.captures, args.masks.parent, args.fields,
                               json.loads(args.masks.read_text()), json.loads((args.captures / 'preview.json').read_text()))
    for name in ('values', 'gates', 'thresholds'):
        result[name].update(extra[name])
        result[name].update(swatches[name])
    result['panel_edges'] = swatches['panel_edges']
    result['measured_streak_widths_m'] = swatches['measured_streak_widths_m']
    result['visibility_fasteners'] = extra['visibility_fasteners']
    result['passed'] = all(result['gates'].values())
    (args.captures / "gates.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({name: value for name, value in result.items() if name not in ("fasteners", "visibility_fasteners")}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
