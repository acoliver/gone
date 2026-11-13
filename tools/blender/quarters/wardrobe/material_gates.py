"""Apply the pilot's per-face finish thresholds to the wardrobe."""
import json
import shutil

import numpy as np
from PIL import Image
import trimesh

from materials import ROOT, HERE, SOURCE, SCRATCH, RUNTIME, FACES, measure, paint_fields, design_paint
from colour import lab, delta_e_2000
from verify_common import uv_report


def main():
    selection = json.loads((SOURCE / 'selection.json').read_text())
    if set(selection) != set(FACES):
        raise ValueError('every wardrobe face requires a passing generated image')
    layout = json.loads((HERE / 'material-layout.json').read_text())
    albedo = np.asarray(Image.open(RUNTIME / 'wardrobe_aged_albedo.png'))
    gates = {}

    def gate(name, value, threshold, passed):
        gates[name] = dict(value=value, threshold=threshold, passed=bool(passed))

    for name, face in FACES.items():
        image = Image.open(SOURCE / selection[name]['chosen']).convert('RGB')
        reference = Image.open(SOURCE / f'{name}-source.png').convert('RGB')
        values = measure(image, reference, face)
        for metric, value in values.items():
            if metric.endswith('delta_e'):
                gate(f'{name}_{metric}', value, '<=8 D65 Lab', value <= 8)
        for metric, limit in [('planar_light_gradient', .06), ('secondary_autocorrelation', .5), ('no_green', .005)]:
            gate(f'{name}_{metric}', values[metric], f'<{limit}' if metric != 'secondary_autocorrelation' else '<=0.5',
                 values[metric] <= limit if metric == 'secondary_autocorrelation' else values[metric] < limit)
        if name != 'hardware':
            gate(f'{name}_edge_broad_ratio', values['edge_broad_ratio'], '>=1.8', values['edge_broad_ratio'] >= 1.8)
        gate(f'{name}_pixels_per_metre', values['pixels_per_metre'], '>=600', values['pixels_per_metre'] >= 600)
        rectangle = np.round(np.array(layout['faces'][name]['uv_rectangle']) * [2048, 4096, 2048, 4096]).astype(int)
        x0, y0, x1, y1 = rectangle
        direct = np.array_equal(albedo[y0:y1, x0:x1, :3], np.asarray(image))
        gate(f'{name}_direct_rgb', direct, 'identical selected generated RGB', direct)
        alpha = np.uint8(np.round((1-paint_fields(image)[1])*255))
        chroma_alpha = np.array_equal(albedo[y0:y1, x0:x1, 3], alpha)
        gate(f'{name}_chroma_relief', chroma_alpha, 'alpha derived only from image chroma', chroma_alpha)
        raw_candidates = list(SOURCE.glob(name + '-[0-9]*.metadata.json'))
        gate(f'{name}_generated_candidates', len(raw_candidates), '>=4', len(raw_candidates) >= 4)
    clean = Image.open(RUNTIME / 'wardrobe_as_built_paint.png').convert('RGB')
    rust = float((paint_fields(clean)[1] < .5).mean())
    gate('as_built_rust', rust, '<0.01', rust < .01)
    mean = lab(np.asarray(clean)/255).mean((0, 1))
    difference = float(delta_e_2000(mean, lab(design_paint())))
    gate('as_built_locker_paint_delta_e', difference, '<=6 D65 Lab', difference <= 6)
    hardware = Image.open(SOURCE / selection['hardware']['chosen'])
    rust = float((paint_fields(hardware)[1] < .5).mean())
    gate('aged_hardware_rust', rust, '>=0.30', rust >= .30)
    for view in ('hero', 'front'):
        for state in ('as_built', 'aged'):
            prefix = SCRATCH / 'render' / f'wardrobe-{state}-{view}'
            regions = np.asarray(Image.open(str(prefix) + '-regions.png'))
            edge, broad = regions[..., 0] > 200, regions[..., 1] > 200
            if not edge.any() or not broad.any():
                raise ValueError(f'missing rendered edge/broad IDs: {prefix}')
            for lane in ('albedo', 'neutral'):
                path = str(prefix) + '-albedo.png' if lane == 'albedo' else str(prefix) + '.png'
                image = Image.open(path).convert('RGB')
                rust = paint_fields(image)[1] < .5
                if state == 'as_built':
                    fraction = float(rust[edge | broad].mean())
                    gate(f'{state}_{view}_{lane}_rust', fraction, '<0.01', fraction < .01)
                else:
                    ratio = float(rust[edge].mean() / max(rust[broad].mean(), 1e-8))
                    gate(f'aged_{view}_{lane}_edge_broad_ratio', ratio, '>=1.8', ratio >= 1.8)
                    fraction = measure_green(image, edge | broad)
                    gate(f'aged_{view}_{lane}_no_green', fraction, '<0.005', fraction < .005)
    scene = trimesh.load(ROOT / 'assets/props/quarters/wardrobe.glb', force='scene')
    uv = uv_report(scene.geometry)
    gate('original_fitted_uvs', uv, 'no overlap, no coordinates outside atlas; density p95/p05<=1.25', uv['pass'])
    masks = json.loads((SCRATCH / 'masks/masks.json').read_text())
    geometry = np.load(SCRATCH / 'geometry.npz')
    occupied = geometry['occupied']
    finite = all(np.isfinite(geometry[key][occupied]).all() for key in ('position', 'normal'))
    density = masks['density_range_px_m']
    gate('mask_bake_finite', finite, 'finite positions, normals, density', finite and np.isfinite(density).all())
    gate('mask_bake_overlap_texels', masks['uv_overlap_texels'], '0', masks['uv_overlap_texels'] == 0)
    stretch = max(density) / min(density)
    gate('mask_bake_density_ratio', stretch, '<=1.015', stretch <= 1.015)
    for name in ('geometry_masks.png', 'weather_masks.png', 'masks.json'):
        shutil.copyfile(SCRATCH / 'masks' / name, SOURCE / name)
    report = dict(prop='wardrobe', age_years=1000, environment='sealed sterile dry oxygenated',
                  gates=gates, passed=sum(row['passed'] for row in gates.values()),
                  failed=sum(not row['passed'] for row in gates.values()),
                  mask_note='The original fitted UVs and exported GLB stay unchanged. The shared bake uses a triangulated scratch copy; image-owned runtime faces have their own measured projection density.')
    (SOURCE / 'gates.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"WARDROBE GATES {report['passed']} passed, {report['failed']} failed")
    for name, row in gates.items():
        if not row['passed']:
            print('FAIL', name, row)
    if report['failed']:
        raise SystemExit(1)


def measure_green(image, mask):
    from locker_gates import hsv
    hue, saturation, _ = hsv(np.asarray(image, float) / 255)
    return float(((hue >= 70) & (hue <= 170) & (saturation > .23))[mask].mean())


if __name__ == '__main__':
    main()
