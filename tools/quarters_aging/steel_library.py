"""Generate reusable whole-face FLUX edits and retain the pilot image gates."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/blender/quarters/wardrobe'))
from materials import measure, face_passes, mute_green, design_paint
from select_locker_faces import calibrate, from_lab
from colour import lab

LIBRARY = ROOT / 'art-source/quarters/steel_library'
SCRATCH = ROOT / 'tmp/mat2/library'
SIZES = {
    'broad': [(384, 768), (384, 768), (640, 640), (640, 640), (768, 384), (768, 384)],
    'strip': [(64, 768), (64, 768), (128, 768), (768, 64), (768, 128)],
    'top': [(640, 640), (768, 512), (768, 512), (768, 256)],
}
CROPS = {'broad': ('docs/art/corridors/hatch-concept-rusted.png', [817, 119, 890, 352]),
         'strip': ('docs/art/quarters/concept-now.png', [438, 259, 459, 319]),
         'top': ('docs/art/quarters/concept-now.png', [656, 272, 720, 304])}


def prepare():
    LIBRARY.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (LIBRARY / '.gdignore').touch()
    rows = []
    for kind, sizes in SIZES.items():
        path, box = CROPS[kind]
        reference = Image.open(ROOT / path).convert('RGB').crop(box)
        reference.save(LIBRARY / f'{kind}-source.png')
        for index, pixels in enumerate(sizes):
            name = f'{kind}-{index:02d}'
            reference.resize(pixels, Image.Resampling.LANCZOS).save(LIBRARY / f'{name}-input.png')
            prompt = (
                'Edit the reference into one flat shadowless edge-to-edge painted warship steel material face. '
                'Muted medium grey-green paint and dark reddish brown iron oxides; preserve reference pigment colours. '
                'After 1000 years in a dry sterile sealed oxygenated ship. '
                'Most of the paint is still intact: broad centre is quiet solid muted grey-green steel paint, '
                'with gentle natural pigment variation. Small thin ragged chips and dark iron oxide concentrate '
                'at outer edges and corners, plus a few isolated tiny fastener scars. '
                'No broad pale peeling, no white patches, no plaster, no stone, no coarse mottling. '
                'No object, hardware, border, frame, seams, perspective, shading, cast shadows or baked illumination. '
                'No periodic marks, straight stripes, regular dots, repeated motifs, mould or biological growth. ')
            if kind == 'top':
                prompt += ('Horizontal upward-facing tabletop: a visible fine soft settled warm grey dust veil, '
                           'delicate diffuse powder softening the paint without hiding it; no footprints, '
                           'no vertical runs, no tracks, no swirls or patches. ')
            elif kind == 'strip':
                prompt += ('A narrow steel trim face, small broken chips near both long edges, '
                           'a mostly intact painted middle. No continuous rust border or long stripe. ')
            else:
                prompt += ('One upright panel, sparse short hairline tapered rust trails below a few '
                           'isolated fixture scars near the upper edges; leave the large centre painted. ')
            (LIBRARY / f'{name}-prompt.txt').write_text(prompt + '\n')
            rows.append(dict(id=name, kind=kind, pixels=list(pixels), size_m=(np.array(pixels)/max(pixels)).tolist(),
                             seed=195000 + len(rows), reference=f'{kind}-source.png',
                             source=path, crop=box, image=f'{name}.png', raw=f'{name}-raw.png'))
    manifest = dict(version=1, age_years=1000, seed=9502, faces=rows,
                    clean='as_built_paint.png', hardware='hardware.png', fabric='fabric.png')
    (LIBRARY / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    paint = tuple(np.uint8(np.round(design_paint()*255)))
    Image.new('RGB', (64, 64), paint).save(LIBRARY / manifest['clean'])
    previous = ROOT / 'art-source/quarters/wardrobe'
    selected = json.loads((previous / 'selection.json').read_text())['hardware']['chosen']
    shutil.copyfile(previous / selected, LIBRARY / manifest['hardware'])
    fabric = ROOT / 'assets/props/quarters/sofa/weave.png'
    # Reuse the approved woven scan without changing the pilot's texture.
    woven = np.asarray(Image.open(fabric).convert('RGB'), float)/255
    luminance = woven.mean(-1)
    woven = np.clip(np.array([.43, .45, .41]) * (.78 + .44*luminance[..., None]), 0, 1)
    Image.fromarray(np.uint8(np.round(woven*255))).save(LIBRARY / manifest['fabric'])
    (LIBRARY / 'shared-provenance.json').write_text(json.dumps(dict(
        hardware=str((previous / selected).relative_to(ROOT)), fabric=str(fabric.relative_to(ROOT)),
        fabric_treatment='grey-green faded pigment multiplied by approved woven scan luminance',
        clean='pilot design_paint() pigment'), indent=2)+'\n')
    return manifest


def generate():
    manifest = prepare()
    for row in manifest['faces']:
        output = LIBRARY / row['raw']
        if output.exists():
            continue
        # Cross-session generation is external and may already own the GPU.
        while True:
            active = subprocess.run(['pgrep', '-f', 'mflux-generate|[g]enerate.py'], capture_output=True, text=True)
            if active.returncode == 1:
                break
            if active.returncode != 0:
                raise RuntimeError(active.stderr)
            print('WAIT GPU', active.stdout.strip(), flush=True)
            time.sleep(15)
        command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                   '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4',
                   '--image-paths', str(LIBRARY / f"{row['id']}-input.png"),
                   '--prompt-file', str(LIBRARY / f"{row['id']}-prompt.txt"),
                   '--seed', str(row['seed']), '--width', str(row['pixels'][0]),
                   '--height', str(row['pixels'][1]), '--output', str(output)]
        print('GENERATE', row['id'], flush=True)
        with (SCRATCH / f"{row['id']}.log").open('w') as log:
            subprocess.run(command, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                           env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1',
                                    TMPDIR=str(SCRATCH)))
        output.with_suffix('.metadata.json').write_text(json.dumps(dict(row, command=command,
            prompt=(LIBRARY / f"{row['id']}-prompt.txt").read_text(), model='FLUX.2-klein-4B',
            quantize=4, steps=4), indent=2)+'\n')
        print('GENERATED', row['id'], flush=True)


def gate_image(image, reference, row):
    values = measure(image, reference, {'size': row['size_m']})
    limits = {key: (8, value <= 8) for key, value in values.items() if key.endswith('delta_e')}
    for key, threshold in [('planar_light_gradient', .06), ('secondary_autocorrelation', .5), ('no_green', .005)]:
        limits[key] = (threshold, values[key] <= threshold if key == 'secondary_autocorrelation' else values[key] < threshold)
    limits['edge_broad_ratio'] = (1.8, values['edge_broad_ratio'] >= 1.8)
    limits['pixels_per_metre'] = (600, values['pixels_per_metre'] >= 600)
    # Keep the wardrobe findings observable, in addition to its existing gates.
    limits['broad_rust'] = (.20, values['broad_rust'] <= .20)
    return values, {key: dict(value=values[key], threshold=limit, passed=bool(passed))
                    for key, (limit, passed) in limits.items()}


def select():
    manifest = json.loads((LIBRARY / 'manifest.json').read_text())
    manifest['faces'] += manifest.get('rejected', [])
    all_gates = {}
    for row in manifest['faces']:
        raw = Image.open(LIBRARY / row['raw']).convert('RGB')
        reference = Image.open(LIBRARY / row['reference']).convert('RGB')
        if 'treatment' in row and (LIBRARY / row['image']).exists():
            values, image_gates = gate_image(Image.open(LIBRARY / row['image']), reference, row)
            row['scores'] = values
            row['passed'] = all(g['passed'] for g in image_gates.values())
            all_gates[row['id']] = image_gates
            continue
        candidates = []
        for amount in (0., .33, .67, 1.):
            image = raw
            if amount:
                a, b = lab(np.asarray(raw)/255), lab(np.asarray(reference)/255)
                q = np.linspace(0, 1, 257)
                corrected = np.stack([np.interp(a[..., c], np.quantile(a[..., c], q),
                                                np.quantile(b[..., c], q)) for c in range(3)], -1)
                image = Image.fromarray(np.uint8(np.round(from_lab(a+(corrected-a)*amount)*255)))
            image, calibration = calibrate(image, reference)
            for radius in (0., .6, 1.):
                result = mute_green(image.filter(ImageFilter.GaussianBlur(radius))) if radius else mute_green(image)
                values, gates = gate_image(result, reference, row)
                failed = sum(not gate['passed'] for gate in gates.values())
                candidates.append((failed, values['broad_high_frequency'], result, values, gates,
                                   dict(quantile_amount=amount, calibration=calibration, denoise_px=radius)))
        best = min(candidates, key=lambda value: value[:2])
        failed, _, image, values, gates, treatment = best
        image.save(LIBRARY / row['image'])
        row['scores'] = values
        row['treatment'] = treatment
        row['passed'] = failed == 0
        all_gates[row['id']] = gates
        print('SELECT', row['id'], failed, values, flush=True)
    rejected = [row for row in manifest['faces'] if not row['passed']]
    manifest['faces'] = [row for row in manifest['faces'] if row['passed']]
    manifest['rejected'] = rejected
    for kind in SIZES:
        if sum(row['kind'] == kind for row in manifest['faces']) < 4:
            raise ValueError(f'fewer than four passing {kind} variants; generate more candidates')
    accepted = {row['id']: all_gates[row['id']] for row in manifest['faces']}
    report = dict(images=accepted, rejected={row['id']: all_gates[row['id']] for row in rejected},
                  passed=sum(g['passed'] for rows in accepted.values() for g in rows.values()),
                  failed=sum(not g['passed'] for rows in accepted.values() for g in rows.values()))
    (LIBRARY / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (LIBRARY / 'gates.json').write_text(json.dumps(report, indent=2)+'\n')
    sheet = Image.new('RGB', (1280, 320*len(SIZES)), '#252b2b')
    draw = ImageDraw.Draw(sheet)
    for k, kind in enumerate(SIZES):
        rows = [row for row in manifest['faces'] if row['kind'] == kind]
        for j, row in enumerate(rows):
            image = Image.open(LIBRARY / row['image'])
            image.thumbnail((200, 280))
            x, y = j*210, k*320
            sheet.paste(image, (x, y+25))
            draw.text((x, y+5), row['id'], fill='white')
    sheet.save(LIBRARY / 'contact-sheet.png')
    if report['failed']:
        raise SystemExit(f"{report['failed']} library gates failed")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['generate', 'select', 'prepare'])
    action = parser.parse_args().action
    {'generate': generate, 'select': select, 'prepare': prepare}[action]()
