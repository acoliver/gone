"""Sparse landmark fitting of the selected full-Hunyuan medal, in metres/Z up."""
import hashlib
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCES = ROOT / 'docs/art/quarters/sheets/medal'
GUIDE = SOURCES / 'c-machined-rim-seed130303-hunyuan-full-seed0-oct320-guide.glb'
GUIDE_HASH = 'cf71dd7144f44bc91e0867ec56f8d23b0289ebf9bf91ec135559f577f4ac26a8'
IMAGE_HASH = '900e566387d32661c16274644f23d14b26a1404bc3ee06931a941c6593eaac3a'
FITTED = HERE / 'medal-fitted.blend'


def sample_guide():
    assert hashlib.sha256(GUIDE.read_bytes()).hexdigest() == GUIDE_HASH
    image = SOURCES / 'c-machined-rim-seed130303.png'
    assert hashlib.sha256(image.read_bytes()).hexdigest() == IMAGE_HASH
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(GUIDE))
    imported = set(bpy.data.objects) - before
    guide = next(o for o in imported if o.type == 'MESH')
    points = np.array([guide.matrix_world @ v.co for v in guide.data.vertices])
    scale = .032 / np.ptp(points[:, 0])
    center = np.array([(points[:, 0].min() + points[:, 0].max()) / 2, 0,
                       points[:, 2].min() + .016 / scale])
    points = (points - center) * scale
    guide.data.calc_loop_triangles()
    tree = BVHTree.FromPolygons(points.tolist(), [tuple(t.vertices) for t in guide.data.loop_triangles], all_triangles=True)
    samples = []
    for radius in np.linspace(.001, .0158, 40):
        for angle in np.linspace(0, 2 * math.pi, 60, endpoint=False):
            x, z = radius * math.cos(angle), radius * math.sin(angle)
            hit, _, _, _ = tree.ray_cast(Vector((x, -.03, z)), Vector((0, 1, 0)))
            if hit is not None:
                samples.append([x, -hit.y, z])
    samples = np.asarray(samples)
    radii = np.linalg.norm(samples[:, [0, 2]], axis=1)
    field = float(np.median(samples[(radii > .008) & (radii < .010), 1]))
    # Fit the fivefold phase and alternating tip/valley radii at sparse spokes.
    angles = np.linspace(0, 2 * math.pi, 180, endpoint=False)
    outline = []
    for angle in angles:
        hits = []
        for radius in np.linspace(.004, .0115, 48):
            hit, _, _, _ = tree.ray_cast(Vector((radius * math.cos(angle), -.03, radius * math.sin(angle))), Vector((0, 1, 0)))
            if hit is None or -hit.y <= field + .00022:
                break
            hits.append(radius)
        outline.append(max(hits) if hits else .004)
    outline = np.array(outline)
    phases = np.linspace(math.pi / 2 - .25, math.pi / 2 + .25, 101)
    scores = [np.mean(np.interp((p + np.arange(5) * 2 * math.pi / 5) % (2 * math.pi), angles, outline, period=2 * math.pi)) for p in phases]
    phase = float(phases[np.argmax(scores)])
    tip = float(np.clip(max(scores), .0098, .0105))
    raw_valley = float(np.mean(np.interp((phase + math.pi / 5 + np.arange(5) * 2 * math.pi / 5) % (2 * math.pi), angles, outline, period=2 * math.pi)))
    valley = float(np.clip(raw_valley, .0048, .0058))
    peak = float(np.quantile(samples[radii < .002, 1], .75))
    relief = float(np.clip((peak - field) * .27, .00065, .0008))
    rings = []
    for lo, hi, kind in [(.0110, .0125, 'crest'), (.0130, .0148, 'channel'), (.0150, .0158, 'crest')]:
        profile = []
        for radius in np.linspace(.001, .0158, 40):
            values = samples[np.isclose(radii, radius, atol=1e-8), 1]
            if lo <= radius <= hi and len(values):
                profile.append((radius, float(np.median(values))))
        radius, depth = (min if kind == 'channel' else max)(profile, key=lambda item: item[1])
        rings.append(dict(radius_m=float(radius), front_m=depth, landmark=kind))
    report = dict(guide_sha256=GUIDE_HASH, image_sha256=IMAGE_HASH, raw_sample_count=len(samples),
                  scale_m_per_raw_unit=scale, raw_center_blender=center.tolist(),
                  raw_samples_x_depth_z_m=samples.tolist(), raw_star_outline_m=outline.tolist(),
                  raw_rings=rings, raw_star_tip_mean_m=float(max(scores)), raw_star_valley_mean_m=raw_valley,
                  raw_star_peak_front_m=peak, fitted_star_phase_rad=phase, fitted_star_tip_m=tip,
                  fitted_star_valley_m=valley, field_front_m=field, relief_m=relief,
                  body_diameter_m=.032, body_depth_m=.00165 + relief,
                  method='40-radius / 60-angle sampling, fivefold landmark averaging; constrained clean concentric quad bands, no dense reprojection')
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    return report


def fitted_surface(report, brass, enamel):
    """One closed quad-band plate, with an integral star and enamel between bands."""
    from build import mesh
    count = 30
    inner = float(np.clip(report['raw_rings'][0]['radius_m'], .0116, .0122))
    channel = float(np.clip(report['raw_rings'][1]['radius_m'], .0134, .0144))
    profile = [(0, 0), (.0155, 0), (.016, .00035), (.016, .00130),
               (.0155, .00165), (channel - .00035, .0011),
               (inner, .0018), (inner - .00055, .00165)]
    vertices, loops = [], []
    phase, tip, valley = (report[k] for k in ['fitted_star_phase_rad', 'fitted_star_tip_m', 'fitted_star_valley_m'])
    polygon = np.array([(r * math.cos(phase + i * math.pi / 5), r * math.sin(phase + i * math.pi / 5))
                        for i, r in enumerate([tip, valley] * 5)])
    angles = phase + np.arange(count) * 2 * math.pi / count
    for radius, depth in profile:
        ids = []
        for angle in angles[:1] if radius == 0 else angles:
            ids.append(len(vertices))
            vertices.append((radius * math.cos(angle), -depth, radius * math.sin(angle)))
        loops.append(ids)
    outline = []
    for angle in angles:
        direction = np.array([math.cos(angle), math.sin(angle)])
        intersections = []
        for i, (a, b) in enumerate(zip(polygon, np.roll(polygon, -1, axis=0))):
            determinant = np.linalg.det(np.column_stack((direction, a - b)))
            if abs(determinant) < 1e-10:
                continue
            radius, t = np.linalg.solve(np.column_stack((direction, a - b)), a)
            if radius > 0 and -1e-7 <= t <= 1 + 1e-7:
                depth = (1 - t) * (.0021 if i % 2 == 0 else .00182) + t * (.00182 if i % 2 == 0 else .0021)
                intersections.append((radius, depth))
        radius, depth = max(intersections)
        outline.append(len(vertices))
        vertices.append((radius * direction[0], -depth, radius * direction[1]))
    loops.append(outline)
    loops.append([len(vertices)])
    vertices.append((0, -(.00165 + report['relief_m']), 0))
    faces, materials = [], []
    for k, (a, b) in enumerate(zip(loops, loops[1:])):
        for i in range(count):
            j = (i + 1) % count
            faces.append((a[0], b[j], b[i]) if len(a) == 1 else
                         (a[i], a[j], b[0]) if len(b) == 1 else (a[i], a[j], b[j], b[i]))
            materials.append(1 if k == len(profile) - 1 else 0)
    obj = mesh('FittedMedalBody', vertices, faces, brass)
    obj.data.materials.append(enamel)
    for face, index in zip(obj.data.polygons, materials):
        face.material_index = index
        face.use_smooth = face.index < (len(loops) - 2) * count
    report['fitted_radial_profile_radius_depth_m'] = profile
    report['inner_ring_star_clearance_m'] = inner - .00055 - tip
    raw = np.asarray(report['raw_samples_x_depth_z_m'])
    radii = np.linalg.norm(raw[:, [0, 2]], axis=1)
    mask = radii > .011
    fitted = np.interp(radii[mask], [r for r, _ in reversed(profile[3:])], [d for _, d in reversed(profile[3:])])
    report['radial_front_deviation_m_p50_p95_max'] = np.quantile(abs(fitted - raw[mask, 1]), [.5, .95, 1]).tolist()
    return obj


def build_source():
    from build import material
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = sample_guide()
    brass = material('Brass', (.66, .43, .14), .8, .3)
    enamel = material('MedalEnamel', (.008, .025, .095), 0, .22)
    body = fitted_surface(report, brass, enamel)
    for obj in (body,):
        obj['generated_guide'] = str(GUIDE.relative_to(ROOT))
        obj['fitting'] = json.dumps({k: v for k, v in report.items() if not k.startswith('raw_samples')})
    bpy.context.scene['medal_fit'] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(FITTED))
    (HERE / 'medal-fit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    build_source()
