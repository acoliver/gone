"""Combine exported, dense-source, alpha-aware render and SAT sofa acceptance."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seat_image_gates import evaluate, visible_dihedrals
from sofa_decay_measure import measure as source_measure
from sofa_decay_policy import ORDER
from sofa_gates import measure as export_measure
from verify import clean
from visible_gates import load

ROOT = Path(__file__).resolve().parents[3]


def render_gates(asset, renders):
    cameras = json.loads((renders/'diagnostics/cameras.json').read_text())
    if cameras['input'] != str(asset.resolve()):
        raise ValueError('Acceptance captures belong to a different GLB')
    result = {key: {} for key in ['G1', 'G2', 'G3', 'G4', 'G6']}
    palette = np.array([[0, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255], [255, 0, 255]])
    for name in [*ORDER, 'Throw']:
        directory = renders/'diagnostics'/name
        mapping = np.load(directory/'faces.npz')
        views = [np.array(Image.open(directory/(view+'.png')).convert('RGB')) for view in ['faces-close', 'faces-hero']]
        visible = visible_dihedrals(mapping['vertices'], mapping['faces'], mapping['ids'], views)
        visible['threshold'] = .09 if name == 'Throw' else .08
        visible['pass'] = visible['fraction'] <= visible['threshold']
        result['G1'][name] = visible
        rgb = np.array(Image.open(directory/'labels.png').convert('RGB'))
        labels = np.argmin(np.sum((rgb[:, :, None].astype(float)-palette)**2, axis=3), axis=2)
        image_result = evaluate(labels, np.array(Image.open(directory/'normals.png').convert('RGB')))
        for key in ['G2', 'G3', 'G4', 'G6']:
            result[key][name] = image_result[key]
    return result


def deposit_gates(asset, record):
    parts, _ = load(asset)
    components = clean(parts['FoamDebris']).split(only_watertight=False)
    floor = np.array([p.centroid[[0, 2]] for p in components if p.bounds[0, 1] < .03])
    expected = [p for p in record['debris']['placements'] if p['floor']]
    reference = np.array([[p['centre_blender_m'][0], -p['centre_blender_m'][1]] for p in expected])
    distances, ids = cKDTree(floor).query(reference)
    if len(expected) != len(floor) or len(np.unique(ids)) != len(expected) or np.max(distances) > .00001:
        raise ValueError('Exported crumb components do not match the measured deposition record')
    sources = []
    for index, spill in enumerate(record['debris']['spills']):
        points = floor[ids[[i for i, p in enumerate(expected) if p['source'] == index]]]
        centre = np.array([spill['origin_blender_m'][0], -spill['origin_blender_m'][1]])
        radii = np.linalg.norm(points-centre, axis=1)
        bins = np.linspace(0, radii.max()+.00001, 6)
        counts = np.histogram(radii, bins)[0]
        density = counts/(np.pi*np.diff(bins*bins))
        rho = float(spearmanr((bins[1:]+bins[:-1])/2, density).statistic)
        powder = spill['powder'] in parts
        sources.append({'source': spill['part'], 'rho': rho, 'bins_m': bins.tolist(),
                        'counts': counts.tolist(), 'density_per_m2': density.tolist(),
                        'powder_present': powder, 'pass': rho <= -.6 and powder})
    library = json.loads((ROOT/'tmp/age/pass4/fragments8/fragments.json').read_text())
    selected = {t['template']: t for t in library['templates'] if t['pass']}
    used = record['debris']['templates']
    templates = {name: {'triangles': selected[name]['reduction']['triangles'],
                        'thickness_width': selected[name]['thickness_width']} for name in used}
    return {'G9': {'templates': templates, 'used': len(used),
                   'pass': len(used) >= 8 and all(14 <= t['triangles'] <= 40 and t['triangles'] != 20 and .25 <= t['thickness_width'] <= .7 for t in templates.values())},
            'G11': {'sources': sources, 'pass': all(s['pass'] for s in sources)}}


def measure(asset, out, renders, collisions, baseline):
    result = export_measure(asset, collisions, out/'sofa-preview-repeat.glb', baseline)
    source = source_measure(out)
    record = json.loads((out/'simulation.json').read_text())
    result['invariants']['all_six_covers_simulated'] = all(
        record['cushions'][name]['simulation']['frames'] > 0 for name in ORDER)
    for key in ['G5', 'G8', 'G17', 'G18', 'G19', 'G32']:
        result['gates'][key] = source['gates'][key]
    for key, parts in render_gates(asset, renders).items():
        result['gates'][key].update(value=parts, status='measured', **{'pass': all(p['pass'] for p in parts.values())})
    for key, value in deposit_gates(asset, record).items():
        result['gates'][key].update(value=value, status='measured', **{'pass': value['pass']})
    for name in ORDER:
        normal = Path(record['materials'][name]['residue']['normal'])
        value = result['gates']['G8']['value'][name]
        value['normal_map_present'] = normal.is_file()
    result['gates']['G8']['pass'] = all(v['rms_m'] >= .0015 and v['normal_map_present'] for v in result['gates']['G8']['value'].values())
    result['not_applicable'] = {f'G{i}': 'tunic-specific; outside the sofa assignment' for i in range(20, 30)}
    result['pass'] = all(g['pass'] for g in result['gates'].values()) and all(result['invariants'].values())
    result['publication_allowed'] = result['pass']
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--renders', type=Path, required=True)
    p.add_argument('--collisions', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    a = p.parse_args()
    result = measure(a.input, a.out, a.renders, a.collisions, a.baseline)
    (a.out/'gates.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['pass'] else 1)
