"""Generalise the wardrobe's numeric source, UV and rendered finish gates."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import trimesh
from PIL import Image

from steel_library import ROOT, LIBRARY, gate_image, design_paint
from map_library import PROPS
from locker_faces import paint_fields
from colour import lab, delta_e_2000
from locker_gates import hsv
sys.path.insert(0, str(ROOT / 'tools/blender/quarters/wardrobe'))
from verify_common import uv_report


def compose(prop, render, output):
    from review_library import archive_review
    sheets = {}
    for view in ('hero', 'front', 'top', 'detail'):
        sheet = Image.new('RGB', (2048, 2048))
        for y, state in enumerate(('as_built', 'aged')):
            for x, identity in enumerate((prop, 'locker')):
                image = Image.open(render / f'{prop}-{identity}-{state}-{view}.png').convert('RGB')
                sheet.paste(image, (x*1024, y*1024))
        sheets[view] = sheet
    changed = False
    for view, sheet in sheets.items():
        path = output / f'matched-{view}.png'
        if not path.exists():
            changed = True
            continue
        previous = Image.open(path).convert('RGB')
        if previous.size != sheet.size or previous.tobytes() != sheet.tobytes():
            changed = True
    if changed: archive_review(output)
    for view, sheet in sheets.items():
        sheet.save(output / f'matched-{view}.png')


def gates(prop, render=None, source_gates=None):
    if source_gates is None: source_gates = {}
    runtime = ROOT / f'assets/props/quarters/steel/{prop}'
    output = LIBRARY / 'props' / prop
    output.mkdir(parents=True, exist_ok=True)
    mapping = json.loads((runtime / 'mapping.json').read_text())
    library = json.loads((LIBRARY / 'manifest.json').read_text())
    images = {row['id']: row for row in library['faces']}
    results = {}

    def gate(name, value, limit, passed):
        results[name] = dict(value=value, threshold=limit, passed=bool(passed))

    used = sorted({face['image'] for face in mapping['faces'] if face['role'] == 'paint'})
    for identity in used:
        if identity not in source_gates:
            row = images[identity]
            image = Image.open(LIBRARY / row['image']).convert('RGB')
            reference = Image.open(LIBRARY / row['reference']).convert('RGB')
            _, source_gates[identity] = gate_image(image, reference, row)
        results.update({identity+'_'+key: value for key, value in source_gates[identity].items()})
    gate('runtime_uv_overlap_texels', mapping['uv_overlap_texels'], '0', mapping['uv_overlap_texels'] == 0)
    gate('fitted_atlas_pixels_per_metre', mapping['density_range'][0], '>=600', mapping['density_range'][0] >= 600)
    source_density = []
    tubes = {}
    for face in mapping['faces']:
        if face['role'] == 'preserved': continue
        filename = images[face['image']]['image'] if face['role'] == 'paint' else library[face['role']]
        pixels = np.array(Image.open(LIBRARY / filename).size)
        physical = face['pitch_m'] if face['role'] in ('hardware', 'fabric') else np.array(face['size_m'])
        source_density.append(float(np.min(pixels/physical)*face['source_density_scale']))
        if face['role'] == 'paint' and face['projection'] == 'cylindrical':
            tubes.setdefault((face['part'], face['kind']), set()).add(face['image'])
    gate('mapped_source_pixels_per_metre', min(source_density), '>=600', min(source_density) >= 600)
    for role, pitch in [('hardware', .2), ('fabric', .1)]:
        matching = [face['pitch_m'] for face in mapping['faces'] if face['role'] == role]
        gate(role+'_physical_pitch_m', sorted(set(matching)), str(pitch), all(value == pitch for value in matching))
    for (part, kind), choices in tubes.items():
        gate(part+'_'+kind+'_continuous_tube_source', sorted(choices), 'one image around the tube', len(choices) == 1)
    # The wardrobe's 1.015 gate belongs to its separate isometric mask bake.
    # Fitted UVs use their existing 1.25 gate and are not repacked for materials.
    scratch = ROOT / f'tmp/mat2/{prop}/mask-bake'
    masks = json.loads((scratch / 'masks/masks.json').read_text())
    geometry = np.load(scratch / 'geometry.npz')
    occupied = geometry['occupied']
    density = masks['density_range_px_m']
    ratio = max(density)/min(density)
    finite = all(np.isfinite(geometry[key][occupied]).all() for key in ('position', 'normal'))
    gate('mask_bake_overlap_texels', masks['uv_overlap_texels'], '0', masks['uv_overlap_texels'] == 0)
    gate('mask_bake_density_ratio', ratio, '<=1.015', ratio <= 1.015)
    gate('mask_bake_finite', finite, 'finite positions, normals and density', finite and np.isfinite(density).all())
    scene = trimesh.load(ROOT / f'assets/props/quarters/{prop}.glb', force='scene')
    uv = uv_report(scene.geometry)
    gate('original_fitted_uvs', uv, 'no overlap, coordinates in atlas, density p95/p05<=1.25', uv['pass'])
    shutil.copyfile(scratch / 'masks/masks.json', output / 'masks.json')
    regions = np.asarray(Image.open(runtime / 'regions.png'))
    painted = (regions[..., 0] > 0) | (regions[..., 1] > 0)
    clean = Image.open(runtime / 'as_built_albedo.png').convert('RGB')
    rust = paint_fields(clean)[1] < .5
    fraction = float(rust[painted].mean())
    gate('as_built_rust', fraction, '<0.01', fraction < .01)
    colour = lab(np.asarray(clean, float)[painted]/255).mean(0)
    difference = float(delta_e_2000(colour, lab(design_paint())))
    gate('as_built_locker_paint_delta_e', difference, '<=6 D65 Lab', difference <= 6)
    hardware = Image.open(LIBRARY / library['hardware']).convert('RGB')
    fraction = float((paint_fields(hardware)[1] < .5).mean())
    gate('aged_hardware_rust', fraction, '>=0.30', fraction >= .30)
    for state in ('as_built', 'aged'):
        for kind in ('albedo', 'normal', 'orm'):
            image = Image.open(runtime / f'{state}_{kind}.png')
            gate(f'{state}_{kind}_atlas', list(image.size), 'square built atlas matching fitted UVs',
                 image.size == (mapping['atlas_size'],)*2)
    if render is not None:
        compose(prop, render, output)
        for view in ('hero', 'front'):
            for state in ('as_built', 'aged'):
                prefix = render / f'{prop}-{prop}-{state}-{view}'
                region = np.asarray(Image.open(str(prefix)+'-regions.png'))
                edge, broad = region[..., 0] > 200, region[..., 1] > 200
                if not edge.any() or not broad.any():
                    raise ValueError(f'no rendered painted edge/broad coverage: {prefix}')
                for lane in ('albedo', 'neutral'):
                    path = str(prefix)+'-albedo.png' if lane == 'albedo' else str(prefix)+'.png'
                    image = Image.open(path).convert('RGB')
                    rust = paint_fields(image)[1] < .5
                    if state == 'as_built':
                        value = float(rust[edge | broad].mean())
                        gate(f'{state}_{view}_{lane}_rust', value, '<0.01', value < .01)
                    else:
                        value = float(rust[edge].mean()/max(rust[broad].mean(), 1e-8))
                        gate(f'{state}_{view}_{lane}_edge_broad_ratio', value, '>=1.8', value >= 1.8)
                        h, s, _ = hsv(np.asarray(image, float)/255)
                        value = float(((h >= 70) & (h <= 170) & (s > .23))[edge | broad].mean())
                        gate(f'{state}_{view}_{lane}_no_green', value, '<0.005', value < .005)
    report = dict(prop=prop, gates=results, age_years=1000, rendered=render is not None,
                  passed=sum(g['passed'] for g in results.values()),
                  failed=sum(not g['passed'] for g in results.values()),
                  atlas_texels_per_metre=mapping['texels_per_metre'],
                  note='Source image density and fitted-UV atlas density are distinct. No geometry or UV repack.')
    (output / 'gates.json').write_text(json.dumps(report, indent=2)+'\n')
    print(prop, report['passed'], 'passed,', report['failed'], 'failed', flush=True)
    for name, row in results.items():
        if not row['passed']:
            print('FAIL', name, row, flush=True)
    return report['failed'] == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=PROPS, action='append')
    parser.add_argument('--render', type=Path)
    args = parser.parse_args()
    source_gates = {}
    passed = [gates(prop, args.render, source_gates) for prop in (args.prop or PROPS)]
    raise SystemExit(0 if all(passed) else 1)
