"""Fit flat pigments through the unchanged Godot sofa preview lighting."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

from finish_calibration import update_albedo
from finish_materials import linear

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'art-source/quarters/sofa'


def sample_target(path, rectangles, kind):
    image = np.asarray(Image.open(path).convert('RGB'))
    samples, patches = [], []
    for x0, y0, x1, y1 in rectangles:
        rgb = image[y0:y1 + 1, x0:x1 + 1].reshape(-1, 3).astype(float)
        maximum, minimum = rgb.max(1), rgb.min(1)
        saturation = (maximum - minimum) / np.maximum(maximum, 1)
        if kind == 'paint':
            selected = (saturation < .18) & (maximum > 30) & (maximum < 190)
        else:
            selected = (saturation > .30) & (rgb[:, 0] > rgb[:, 1] * 1.08) & (rgb[:, 1] > rgb[:, 2] * 1.08) & (maximum > 35) & (maximum < 220)
        if not selected.any():
            raise ValueError('No reference pigment pixels in patch: ' + str((x0, y0, x1, y1)))
        values = rgb[selected]
        samples.append(values)
        patches.append(dict(rectangle=[x0, y0, x1, y1], pixels=len(values), median=np.median(values, axis=0).tolist()))
    return np.median(np.concatenate(samples), axis=0), patches


def calibrate(out):
    out.mkdir(parents=True, exist_ok=True)
    sheet = ROOT / 'docs/art/quarters/sheets/sofa'
    definitions = {
        'paint': dict(image='hero.png', rectangles=[[104, 479, 218, 516], [132, 651, 246, 678], [360, 688, 472, 713]], position=[0, .24, .475], normal=[0, 0, 1], light='neutral'),
        'foam': dict(image='aged-target.png', rectangles=[[357, 578, 389, 595], [572, 610, 594, 627], [397, 420, 415, 443]], position=[-.18, .43, .29], normal=[0, 1, 0], light='present'),
        'crumb': dict(image='aged-target.png', rectangles=[[167, 790, 365, 855], [454, 866, 694, 918]], position=[0, .012, .58], normal=[0, 1, 0], light='present'),
    }
    record, swatches = {}, {}
    for role, definition in definitions.items():
        target, patches = sample_target(sheet / definition['image'], definition['rectangles'], role)
        record[role] = dict(reference=definition['image'], selection='neutral s<.18, 30<v<190' if role == 'paint' else 'warm pixels s>.30, r>1.08g, g>1.08b, 35<v<220', patches=patches, target_display_rgb=target.tolist(), attempts=[])
        swatches[role] = {key: definition[key] for key in ['position', 'normal', 'light']}
        swatches[role]['albedo'] = linear(target / 255).tolist()
    for iteration in range(8):
        (out / 'swatches.json').write_text(json.dumps(swatches, indent=2) + '\n')
        with (out / ('swatches-%d.log' % iteration)).open('w') as log:
            subprocess.run(['godot', '--path', str(ROOT), '-s', 'tools/blender/quarters/sofa/calibration_preview.gd', '--', '--out', str(out)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        converged = True
        for role, swatch in swatches.items():
            image = np.asarray(Image.open(out / (role + '.png')).convert('RGB'))
            displayed = np.median(image[480:544, 480:544], axis=(0, 1))
            target = np.asarray(record[role]['target_display_rgb'])
            record[role]['attempts'].append(dict(linear_albedo=swatch['albedo'], displayed_rgb=displayed.tolist()))
            shutil.copyfile(out / (role + '.png'), out / ('%s-%d.png' % (role, iteration)))
            if np.max(np.abs(displayed - target)) > 1:
                converged = False
                swatch['albedo'] = update_albedo(np.asarray(swatch['albedo']), displayed, target).tolist()
        if converged:
            break
    else:
        raise ValueError('Swatch fitting did not converge within one sRGB byte')
    for role in record:
        record[role]['linear_albedo'] = record[role]['attempts'][-1]['linear_albedo']
        record[role]['displayed_rgb'] = record[role]['attempts'][-1]['displayed_rgb']
        record[role].update({key: definitions[role][key] for key in ['position', 'normal', 'light']})
    record['scene'] = dict(renderer='Godot Forward+ Metal', tone_mapping='linear', ambient_present=.20, ambient_neutral=.55, ceiling_position=[-.6, 1.46, 1.25], note='Warm-pixel segmentation excludes floor and cloth around irregular foam tears. Swatches fit regional pigment display, not complete target illumination.')
    (SOURCE / 'finish-calibration.json').write_text(json.dumps(record, indent=2) + '\n')
    (out / 'finish-calibration.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'tmp/mat/sofa2/calibration')
    calibrate(parser.parse_args().out)
