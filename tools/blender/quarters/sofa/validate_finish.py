"""Check sofa finish exports, rail texel density and lit debris visibility."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from uv_metrics import measure
from validate_material_pilot import geometry, renders

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'tmp/mat/sofa2'
OLD = ROOT / 'tmp/mat/sofa'


def debris(directory):
    image = lambda name: np.asarray(Image.open(directory / name).convert('RGB'), float)
    from finish_calibration import linear
    opacity = linear(image('debris-mask.png') / 255).min(2)
    covered = opacity >= .05
    if not covered.any():
        raise ValueError('No visible floor-debris coverage')
    delta = np.abs(image('debris-on.png') - image('debris-off.png')).max(2)[covered]
    return dict(visible_pixels=int(covered.sum()), minimum_coverage=.05,
                fully_covered_pixels=int((opacity > .98).sum()),
                mean_max_channel_srgb_levels=float(delta.mean()),
                median_max_channel_srgb_levels=float(np.median(delta)),
                fraction_at_least_8_levels=float((delta >= 8).mean()))


def main():
    report = dict(geometry={}, rail_uv={}, repeat_exports={})
    for state, file in [('as_built', 'sofa.glb'), ('aged', 'sofa_aged.glb')]:
        baseline = OLD / 'as-built-geometry-base.glb' if state == 'as_built' else ROOT / 'tmp/age/pass10/sofa-preview.glb'
        report['geometry'][state] = geometry(baseline, ROOT / 'assets/props/quarters' / file)
        same = (ROOT / 'assets/props/quarters' / file).read_bytes() == (OUT / state / 'repeat.glb').read_bytes()
        report['repeat_exports'][state] = same
        assert same, 'byte-identical saved-source re-export: ' + state
        report['rail_uv'][state] = {}
        for name, directory in [('before', OLD), ('after', OUT)]:
            data = np.load(directory / state / 'Frame__0.npz')
            report['rail_uv'][state][name] = measure(data['uv'], data['positions'], 1024)
        current = report['rail_uv'][state]['after']
        assert current['overlap_fraction'] < .001, 'separate metal charts'
        assert current['anisotropy_p90'] < 2, 'near-isotropic metal texel density'
    report.update(renders(OUT, OLD / 'locker-before'))
    assert all(value['pass'] for value in report['no_green'].values()), 'no green in lit albedo views'
    assert all(value['pass'] for value in report['visible_dust'].values()), 'retained visible dust'
    report['debris'] = debris(OUT)
    assert report['debris']['median_max_channel_srgb_levels'] >= 8, 'visible floor debris contrast'
    assert report['debris']['fraction_at_least_8_levels'] >= .5, 'visible contrast over most floor debris'
    gates = json.loads((ROOT / 'tools/blender/quarters/sofa/pass10-material-pilot-gates.json').read_text())
    # All retained geometry, including the fragments and powder, is checked above.
    report['retained_debris_gates'] = {name: gates['gates'][name] for name in ['G9', 'G10', 'G11']}
    assert all(value['pass'] for value in report['retained_debris_gates'].values())
    (OUT / 'finish-gates.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({name: value for name, value in report.items() if name not in ['geometry', 'retained_debris_gates']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    OUT = parser.parse_args().out.resolve()
    main()
