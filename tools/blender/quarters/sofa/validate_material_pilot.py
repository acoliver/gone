"""Check exported sofa positions/pivots, deterministic bytes and render gates."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools/blender/quarters_aging'))
from verify import load
sys.path.insert(0, str(ROOT / 'tools/quarters_aging'))
from locker_gates import newly_green, rgb

OUT = ROOT / 'tmp/mat/sofa'


def geometry(before_path, after_path):
    before, old_doc = load(before_path)
    after, new_doc = load(after_path)
    assert before.keys() == after.keys(), 'same exported names'
    poses = lambda doc: {node['name']: {k: node[k] for k in ['translation', 'rotation', 'scale', 'matrix'] if k in node} for node in doc['nodes'] if 'mesh' in node}
    assert poses(old_doc) == poses(new_doc), 'same local pivots'
    parts = {}
    for name in before:
        first, second = before[name], after[name]
        distances = [cKDTree(a.vertices).query(b.vertices)[0].max() for a, b in [(first, second), (second, first)]]
        assert len(first.faces) == len(second.faces), name + ': triangle count'
        assert max(distances) < 1e-7, name + ': unchanged positions'
        parts[name] = dict(triangles=len(second.faces), maximum_position_delta_m=float(max(distances)), bounds_y_up_m=second.bounds.tolist())
    return dict(parts=parts, names_identical=True, pivots_identical=True, maximum_position_delta_m=max(p['maximum_position_delta_m'] for p in parts.values()))


def renders():
    results = {}
    for angle in ['hero', 'front', 'detail', 'top', 'streaks']:
        aged = rgb(OUT / ('aged-albedo-' + angle + '.png'))
        ids = rgb(OUT / ('aged-ids-' + angle + '.png'))
        covered = (ids[..., 0] > .5) & (ids[..., 2] > .5)
        largest, total = newly_green(np.zeros_like(aged), aged, covered)
        results[angle] = dict(no_green_largest_region=largest, no_green_total=total, **{'pass': total < .005})
    dust = {}
    for light in ['neutral', 'present']:
        enabled = rgb(OUT / ('aged-' + light + '-top.png'))
        disabled = rgb(OUT / ('aged-nodust-' + light + '-top.png'))
        ids = rgb(OUT / 'aged-ids-top.png')
        regions = rgb(OUT / 'aged-regions-top.png')
        covered = (ids[..., 0] > .5) & (ids[..., 2] > .5) & (regions[..., 2] > .7)
        delta = np.abs(enabled - disabled).max(2)
        changed = float((delta[covered] >= 8 / 255).mean())
        dust[light] = dict(up_face_pixels=int(covered.sum()), changed_by_8_levels_fraction=changed,
                           mean_absolute_srgb_delta=float(delta[covered].mean()),
                           threshold='>=0.05 of visible up-face pixels change by >=8/255', **{'pass': changed >= .05})
    before, after = OUT / 'locker-before', OUT / 'locker-after'
    names = sorted(p.name for p in before.glob('*.png'))
    same = [name for name in names if (before / name).read_bytes() == (after / name).read_bytes()]
    assert names and len(same) == len(names), 'locker rendered PNG bytes unchanged'
    return dict(no_green=results, visible_dust=dust, locker=dict(compared=len(names), identical=len(same), **{'pass': len(same) == len(names)}))


def main():
    report = dict(aged_geometry=geometry(ROOT / 'tmp/age/pass10/sofa-preview.glb', ROOT / 'assets/props/quarters/sofa_aged.glb'),
                  as_built_geometry=geometry(OUT / 'as-built-geometry-base.glb', ROOT / 'assets/props/quarters/sofa.glb'))
    report['repeat_exports'] = {state: (ROOT / 'assets/props/quarters' / file).read_bytes() == (OUT / state / 'repeat.glb').read_bytes() for state, file in [('aged', 'sofa_aged.glb'), ('as_built', 'sofa.glb')]}
    if (OUT / 'aged-albedo-hero.png').exists() and (OUT / 'locker-after').exists():
        report.update(renders())
    (OUT / 'material-gates.json').write_text(json.dumps(report, indent=2) + '\n')
    assert all(report['repeat_exports'].values()), 'byte-identical exports'
    if 'no_green' in report:
        assert all(row['pass'] for row in report['no_green'].values()), 'no green'
        assert all(row['pass'] for row in report['visible_dust'].values()), 'visible dust'
    print(json.dumps({key: value for key, value in report.items() if not key.endswith('geometry')}, indent=2))


if __name__ == '__main__':
    main()
