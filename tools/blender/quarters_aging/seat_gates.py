"""Centre-seat acceptance on exported triangles, dense sources and lit-camera passes."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
import trimesh

from collision_policy import rigid_counts
from seat_image_gates import evaluate, visible_dihedrals
from sofa_gates import dihedral_share, missing_gates, rounded_box_rms, vertical_area
from verify import clean
from visible_gates import heights, load

ROOT = Path(__file__).resolve().parents[3]
REQUIRED = [*[f'G{i}' for i in range(1, 9)], 'G12', 'G13', 'G14', 'G30', 'G32']


def surface(part, prefix):
    meshes = [m for name, m in part.metadata['raw_primitives'].items() if name.startswith(prefix)]
    if not meshes:
        raise ValueError(f'No exported {prefix} material surface')
    return trimesh.util.concatenate(meshes)


def crust_roughness(path):
    data = np.load(path)
    mesh = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
    points = mesh.vertices[mesh.vertex_normals[:, 2] > .25]
    tree = cKDTree(points)
    samples = points[np.linspace(0, len(points)-1, min(1000, len(points))).astype(int)]
    rms = []
    for ids in tree.query_ball_point(samples, .010):
        patch = points[ids]
        if len(patch) < 6:
            continue
        centred = patch-patch.mean(0)
        normal = np.linalg.svd(centred, full_matrices=False)[2][-1]
        rms.append(np.sqrt(np.mean((centred@normal)**2)))
    if not rms:
        raise ValueError('No upper residue patches for 20 mm plane fits')
    return {'rms_m': float(np.sqrt(np.mean(np.square(rms)))), 'patches': len(rms),
            'quantiles_m': np.quantile(rms, [.1, .5, .9]).tolist()}


def seat_contacts(sat, baseline):
    selected = {n for n in sat['self'] if n == 'SeatCushion_C' or n.startswith('SeatCushion_C_')}
    if 'SeatCushion_C' not in selected:
        raise ValueError('SAT report has no centre seat')
    contacts = {'self/'+n: v['count'] for n, v in sat['self'].items() if n in selected}
    contacts.update({n: v['count'] for n, v in sat['pairs'].items() if set(n.split('/')) & selected})
    count = sum(contacts.values())
    rigid_equal = rigid_counts(sat) == rigid_counts(baseline)
    return {'changed_intersections': count, 'pairs': contacts, 'rigid_baseline': rigid_counts(baseline),
            'rigid_actual': rigid_counts(sat), 'rigid_baseline_unchanged': rigid_equal,
            'pass': count == 0 and rigid_equal}


def measure(asset, trial_dir, renders, collisions, baseline):
    after, _ = load(asset)
    before, _ = load(ROOT/'assets/props/quarters/sofa.glb')
    record = json.loads((trial_dir/'seat-trial.json').read_text())
    gates = missing_gates()
    def measured(key, value, passed):
        gates[key].update(value=value, status='measured', **{'pass': bool(passed)})
    cover = surface(after['SeatCushion_C'], 'CharcoalUpholstery')
    residue = clean(surface(after['SeatCushion_C'], 'Foam'))
    g1 = dihedral_share(clean(cover))
    measured('G1', g1, g1 <= .08)
    gates['G1']['method'] = 'All exported sheet adjacencies; conservative superset of visible adjacencies'
    if (renders/'seat-labels.png').exists() and (renders/'seat-normals.png').exists():
        camera = json.loads((renders/'seat-camera.json').read_text())
        if camera['input'] != str(asset.resolve()):
            raise ValueError('Diagnostic renders do not belong to the requested export')
        mapping = np.load(renders/'seat-face-map.npz')
        views = [np.array(Image.open(renders/f'seat-faces-{view}.png').convert('RGB')) for view in ['close', 'hero']]
        visible = visible_dihedrals(mapping['vertices'], mapping['faces'], mapping['ids'], views)
        measured('G1', visible, visible['pass'])
        gates['G1']['method'] = 'Adjacent exported faces visible together in alpha-tested close and hero face-ID passes'
        rgb = np.array(Image.open(renders/'seat-labels.png').convert('RGB'))
        palette = np.array([[0, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255], [255, 0, 255]])
        labels = np.argmin(np.sum((rgb[:, :, None].astype(float)-palette)**2, axis=3), axis=2)
        image_gates = evaluate(labels, np.array(Image.open(renders/'seat-normals.png').convert('RGB')))
        for key in ['G2', 'G3', 'G4', 'G6']:
            data = image_gates[key]
            measured(key, data, data['pass'])
    measured('G5', record['G5']['fraction'], record['G5']['pass'])
    planar = float(residue.facets_area[residue.facets_area > .001].sum()/residue.area)
    measured('G7', planar, planar <= .05)
    roughness = crust_roughness(trial_dir/'dense-residue.npz')
    roughness['normal_map_present'] = Path(record['residue_maps']['normal']).is_file()
    measured('G8', roughness, roughness['rms_m'] >= .0015 and roughness['normal_map_present'])
    walls = vertical_area(cover)/vertical_area(before['SeatCushion_C'])
    measured('G12', walls, walls <= .25)
    error = rounded_box_rms(cover.vertices)
    measured('G13', error, error >= .012)
    cx = before['SeatCushion_C'].centroid[0]
    x, z = np.meshgrid(np.linspace(cx-.08, cx+.08, 7), np.linspace(.02, .17, 7))
    xy = np.c_[x.ravel(), z.ravel()]
    old, new = heights(before['SeatCushion_C'], xy), heights(cover, xy)
    valid = np.isfinite(old) & np.isfinite(new)
    centre = float(np.median((new[valid]-.3898)/(old[valid]-.3898))) if valid.any() else None
    measured('G14', centre, centre is not None and .1 <= centre <= .25)
    if collisions is not None:
        contacts = seat_contacts(json.loads(collisions.read_text()), json.loads(baseline.read_text()))
        measured('G30', contacts, contacts['pass'])
    boundary = record['cover_decimation']['boundary_hausdorff_upper_m']
    measured('G32', boundary, boundary <= .0015)
    return {'scope': 'centre seat only; other parts are unaccepted sofa-k comparison geometry',
            'input': str(asset), 'gates': gates, 'required': REQUIRED,
            'seat_pass': all(gates[key]['pass'] for key in REQUIRED), 'pass': all(g['pass'] for g in gates.values())}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--trial', type=Path, required=True)
    p.add_argument('--renders', type=Path, required=True)
    p.add_argument('--collisions', type=Path)
    p.add_argument('--baseline', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = measure(a.input, a.trial, a.renders, a.collisions, a.baseline)
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['seat_pass'] else 1)
