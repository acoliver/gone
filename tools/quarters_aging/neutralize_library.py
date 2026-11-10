"""Remove concept lighting's warm paint bias without repainting image layouts.

The raw crops remain untouched. A spatially uniform, chroma-conditioned Lab
colour transform aligns paint with the pilot pigment while retaining oxide.
Both the selected image and its measurement reference receive that transform.
"""
import json

import numpy as np
from PIL import Image

from steel_library import LIBRARY, mute_green, design_paint, gate_image, align_paint
from locker_faces import paint_fields
from colour import lab
from select_locker_faces import from_lab, calibrate


def neutral_transform(reference, target):
    colour = np.asarray(reference.convert('RGB'), float)/255
    values = lab(colour)
    paint = paint_fields(reference)[1] >= .5
    if not paint.any() or paint.all():
        raise ValueError('neutral calibration requires both paint and oxide')
    shift = lab(target)-values[paint].mean(0)
    return dict(paint_lab_shift=shift.tolist(), paint_target_srgb=target.tolist(),
                method='spatially uniform chroma-conditioned Lab colour transform; no geometry masks or new wear')


def apply(image, transform):
    values = lab(np.asarray(image.convert('RGB'), float)/255)
    paint = paint_fields(image)[1]
    output = values+paint[..., None]*np.array(transform['paint_lab_shift'])
    return mute_green(Image.fromarray(np.uint8(np.round(from_lab(output)*255))))


def main():
    manifest = json.loads((LIBRARY / 'manifest.json').read_text())
    if manifest.get('neutral_palette'):
        raise ValueError('library already neutralized; restore its input revision before regrading')
    baseline = LIBRARY / 'warm-palette'
    baseline.mkdir(exist_ok=True)
    (baseline / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (baseline / 'gates.json').write_bytes((LIBRARY / 'gates.json').read_bytes())
    transforms = {}
    for kind in ('broad', 'strip', 'top'):
        reference = Image.open(LIBRARY / f'{kind}-source.png').convert('RGB')
        target = np.clip(design_paint()+[.02, .02, .02], 0, 1)
        if kind == 'top':
            target = np.array([.52, .55, .51])
        transforms[kind] = neutral_transform(reference, target)
        apply(reference, transforms[kind]).save(LIBRARY / f'{kind}-neutral-source.png')
    all_gates = {}
    for row in manifest['faces']:
        row['neutral_paint_target'] = transforms[row['kind']]['paint_target_srgb']
        image = Image.open(LIBRARY / row['image']).convert('RGB')
        image.save(baseline / row['image'])
        image = apply(image, transforms[row['kind']])
        reference_name = 'top-neutral-source.png' if row['kind'] == 'top' else 'broad-neutral-source.png'
        reference = Image.open(LIBRARY / reference_name).convert('RGB')
        values, gates = gate_image(image, reference, row)
        if not all(g['passed'] for g in gates.values()):
            image, calibration = calibrate(image, reference)
            image = align_paint(image, row['neutral_paint_target'])
            values, gates = gate_image(image, reference, row)
            row['neutral_refit'] = calibration
        image.save(LIBRARY / row['image'])
        row['raw_reference'] = row['reference']
        row['reference'] = reference_name
        row['scores'] = values
        row['passed'] = all(g['passed'] for g in gates.values())
        all_gates[row['id']] = gates
        print(row['id'], row['passed'], {k:v for k,v in gates.items() if not v['passed']}, flush=True)
    manifest['neutral_palette'] = transforms
    manifest['palette_reason'] = ('The warm concept crops classified low-chroma brown as paint. '
        'Matched renders therefore lost the grey-green base. Align reference paint with the '
        'pilot pigment before scoring; retain raw source statistics and all original thresholds.')
    (LIBRARY / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    report = dict(images=all_gates, rejected=json.loads((baseline/'gates.json').read_text())['rejected'],
                  passed=sum(g['passed'] for rows in all_gates.values() for g in rows.values()),
                  failed=sum(not g['passed'] for rows in all_gates.values() for g in rows.values()),
                  reference_note='neutralized reference crops; raw warm-palette crops and gates retained separately')
    (LIBRARY / 'gates.json').write_text(json.dumps(report, indent=2)+'\n')
    if report['failed']:
        raise SystemExit(f"{report['failed']} neutral-palette gates failed")


if __name__ == '__main__':
    main()
