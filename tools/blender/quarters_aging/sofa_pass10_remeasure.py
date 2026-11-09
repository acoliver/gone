"""Apply the pass-11 visible-boundary metrics to the accepted pass-10 pilot."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_decay_policy import ORDER
from sofa_pass8_accept import project
from sofa_pass11_metrics import cloth_coverage, visible_gashes


def tear_segments(directory, name, record):
    stem = 'throw' if name == 'Throw' else name
    data = np.load(directory / (stem + '-game.npz'))
    faces, points = data['faces'], data['vertices']
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    segments = points[unique[counts == 1]]
    centres = segments.mean(1)
    if name == 'Throw':
        opening = record['throw']['materials']['opacity']['opening']
        # The worn arm opening is distinct from the long exterior hem.
        distance = np.linalg.norm(centres - opening['centre'], axis=1)
        return segments[distance < .15]
    lips = np.load(directory / (name + '-lip-classes.npz'))
    distance, index = cKDTree(lips['points']).query(centres)
    return segments[(distance < .015) & (lips['classes'][index] == 'tear')]


def measure(directory, renders):
    result = json.loads((directory / 'gates.json').read_text())
    record = json.loads((directory / 'simulation.json').read_text())
    cameras = json.loads((renders / 'diagnostics/cameras.json').read_text())['parts']
    values = {key: {} for key in ['G3', 'G4', 'G6']}
    for name in [*ORDER, 'Throw']:
        segments = tear_segments(directory, name, record)
        outlines = []
        views = ['labels', 'crease-labels'] if name == 'Throw' else ['labels']
        for view in views:
            rgb = np.asarray(Image.open(renders / 'diagnostics' / name / (view + '.png')).convert('RGB'))
            projected = project(segments.reshape(-1, 3), cameras[name][view]).reshape(-1, 2, 2)[:, :, ::-1]
            occluded = (rgb[:, :, 0] > 180) & (rgb[:, :, 2] > 180)
            found = visible_gashes(cloth_coverage(rgb), projected, radius=32., occluded=occluded)
            for outline in found:
                outline['camera'] = view
            outlines.extend(found)
        runs = [o['longest_straight_run_px'] for o in outlines]
        widths = [o['width_cv'] for o in outlines]
        dimensions = [o['contour_dimension'] for o in outlines if o['maximum_extent_px'] >= 64]
        previous = result['gates']['G3']['value'][name]
        seam = previous.get('seam_fringe_and_gape_pass', True)
        values['G3'][name] = dict(value=runs, outlines=outlines, seam_fringe_and_gape_pass=seam,
                                  **{'pass': bool(runs) and max(runs) <= 12 and seam})
        values['G4'][name] = dict(value=widths, **{'pass': bool(widths) and all(w is not None and w >= .35 for w in widths)})
        values['G6'][name] = dict(value=dimensions, minimum_extent_px=64,
                                  **{'pass': bool(dimensions) and all(1.15 <= d <= 1.40 for d in dimensions)})
    for key, parts in values.items():
        result['gates'][key].update(value=parts, **{'pass': all(p['pass'] for p in parts.values())},
            method='pass-11 combined R+G antialiased coverage and open-lip metrics; physical pass-10 panel boundaries; seam checks retained')
    result['pass'] = all(g['pass'] for g in result['gates'].values()) and all(result['invariants'].values())
    result['publication_allowed'] = True
    result['pilot_exception'] = 'Andrew accepted pass 10 for the material pilot; failed thresholds remain unchanged.'
    result['source'] = str(directory / 'sofa-preview.glb')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--renders', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.source, args.renders)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print({k: v['pass'] for k, v in result['gates'].items()})
