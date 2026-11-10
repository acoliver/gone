"""Dense-source and game-surface measurements for the ordered sofa trial."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.signal import find_peaks
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seat_gates import crust_roughness
from sofa_decay_policy import DECK, ORDER
from sofa_gates import dihedral_share, missing_gates, rounded_box_rms, vertical_area, volume_below
from visible_gates import heights, load

ROOT = Path(__file__).resolve().parents[3]


def surface(path, gltf=False):
    data = np.load(path)
    points = data['vertices'].copy()
    if gltf:
        points = points[:, [0, 2, 1]]
        points[:, 2] *= -1
    return trimesh.Trimesh(points, data['faces'], process=True)


def front_folds(mesh):
    """Measure forward crests on five vertical front profiles, at 1 mm sampling."""
    x0, y0, z0 = mesh.bounds[0]
    x1, y1, z1 = mesh.bounds[1]
    z = np.arange(z0+.002, z1-.002, .001)
    counts = []
    profiles = []
    for x in np.linspace(x0+.15*(x1-x0), x1-.15*(x1-x0), 5):
        origins = np.c_[np.full(len(z), x), np.full(len(z), y0-.1), z]
        hits, rays, _ = mesh.ray.intersects_location(origins, np.tile([0, 1, 0], (len(z), 1)), multiple_hits=True)
        front = np.full(len(z), np.inf)
        if len(hits):
            np.minimum.at(front, rays, hits[:, 1])
        valid = np.isfinite(front)
        if valid.sum() < 8:
            counts.append(0)
            continue
        values = np.interp(np.arange(len(z)), np.flatnonzero(valid), front[valid])
        peaks, properties = find_peaks(-values, prominence=.008, distance=8)
        counts.append(len(peaks))
        profiles.append({'x_m': float(x), 'fold_z_m': z[peaks].tolist(),
                         'prominences_m': properties['prominences'].tolist()})
    return {'folds': int(np.median(counts)), 'profile_counts': counts, 'profiles': profiles,
            'minimum_prominence_m': .008}


def throw_connectivity(mesh):
    parts = mesh.split(only_watertight=False)
    bridges = 0
    for part in parts:
        p = part.vertices
        arm = ((p[:, 0] >= .93) & (p[:, 0] <= 1.12) &
               (p[:, 1] >= -.46) & (p[:, 1] <= .22) & (p[:, 2] >= .76))
        if arm.any() and p[:, 2].min() <= .015:
            bridges += 1
    return {'components': len(parts), 'arm_to_floor_components': bridges,
            'continuous_arm_to_floor': bridges == 1 and len(parts) <= 2}


def throw_fall(mesh):
    continuity = throw_connectivity(mesh)
    selected = mesh.triangles_center[:, 2] < .30
    if not selected.any():
        return {**continuity, 'distance_m': None, 'folds': 0, 'pass': False}
    centre = np.average(mesh.triangles_center[selected], weights=mesh.area_faces[selected], axis=0)
    nearest = np.clip(centre[:2], [.95, -.44], [1.11, .20])
    distance = float(np.linalg.norm(centre[:2]-nearest))
    low = mesh.submesh([np.flatnonzero(selected)], append=True)
    counts, profiles = [], []
    for axis in [0, 1]:
        along = np.linspace(low.bounds[0, axis], low.bounds[1, axis], 400)
        other = float(np.median(low.vertices[:, 1-axis]))
        origins = np.zeros((len(along), 3))
        origins[:, axis] = along
        origins[:, 1-axis] = other
        origins[:, 2] = .32
        hit, rays, _ = low.ray.intersects_location(origins, np.tile([0, 0, -1], (len(along), 1)), multiple_hits=True)
        heights_ = np.full(len(along), -np.inf)
        np.maximum.at(heights_, rays, hit[:, 2])
        valid = np.isfinite(heights_)
        if valid.sum() < 8:
            counts.append(0)
            continue
        values = np.interp(np.arange(len(along)), np.flatnonzero(valid), heights_[valid])
        peaks, properties = find_peaks(values, prominence=.010, distance=8)
        counts.append(len(peaks))
        profiles.append({'axis': axis, 'fold_positions_m': along[peaks].tolist(),
                         'prominences_m': properties['prominences'].tolist()})
    folds = max(counts, default=0)
    return {**continuity, 'distance_m': distance, 'folds': folds, 'profiles': profiles,
            'fallen_centroid_blender_m': centre.tolist(),
            'pass': distance <= .25 and folds >= 3 and continuity['continuous_arm_to_floor']}


def measure(out):
    before, _ = load(ROOT/'assets/props/quarters/sofa.glb')
    record = json.loads((out/'simulation.json').read_text())
    gates = missing_gates()
    values = {key: {} for key in ['G1', 'G5', 'G7', 'G8', 'G12', 'G13', 'G14', 'G15', 'G16', 'G17', 'G32']}
    for name in ORDER:
        path = out/(name+'-game.npz')
        if not path.exists():
            continue
        cover = surface(path, True)
        detail = record['cushions'][name]
        values['G1'][name] = dihedral_share(cover)
        values['G5'][name] = detail['G5']['fraction']
        values['G32'][name] = detail['cover_decimation']['boundary_hausdorff_upper_m']
        residue_path = out/(name+'-game-residue.npz')
        if residue_path.exists():
            residue = surface(residue_path, True)
            values['G7'][name] = float(residue.facets_area[residue.facets_area > .001].sum()/residue.area)
            values['G8'][name] = crust_roughness(out/(name+'-dense-residue.npz'))
        if name.startswith('Seat'):
            values['G12'][name] = vertical_area(cover)/vertical_area(before[name])
            values['G13'][name] = rounded_box_rms(cover.vertices)
            cx = before[name].centroid[0]
            x, z = np.meshgrid(np.linspace(cx-.08, cx+.08, 7), np.linspace(.02, .17, 7))
            xy = np.c_[x.ravel(), z.ravel()]
            old, new = heights(before[name], xy), heights(cover, xy)
            valid = np.isfinite(old) & np.isfinite(new)
            values['G14'][name] = float(np.median((new[valid]-DECK)/(old[valid]-DECK))) if valid.any() else None
        else:
            base = before[name].bounds[0, 1]
            values['G15'][name] = float((cover.bounds[1, 1]-base)/before[name].extents[1])
            if residue_path.exists():
                values['G16'][name] = volume_below(residue, base+before[name].extents[1]/3)/abs(residue.volume)
            values['G17'][name] = front_folds(surface(path))
    limits = {'G1': lambda v: v <= .08, 'G5': lambda v: v >= .30, 'G7': lambda v: v <= .05,
              'G8': lambda v: v['rms_m'] >= .0015 and bool(record.get('materials')),
              'G12': lambda v: v <= .25, 'G13': lambda v: v >= .012,
              'G14': lambda v: v is not None and .1 <= v <= .25,
              'G15': lambda v: .4 <= v <= .65, 'G16': lambda v: v >= .6,
              'G17': lambda v: v['folds'] >= 2, 'G32': lambda v: v <= .0015}
    for key, parts in values.items():
        needed = 3 if key in {'G12', 'G13', 'G14', 'G15', 'G16', 'G17'} else 6
        if parts:
            passed = len(parts) == needed and all(limits[key](v) for v in parts.values())
            gates[key].update(value=parts, status='measured' if len(parts) == needed else 'partial', **{'pass': passed})
    if 'throw' in record:
        share = record['throw']['splits']['split_share']
        gates['G18'].update(value=share, status='measured', **{'pass': .6 <= share <= .9})
        fall = throw_fall(surface(out/'throw-game.npz'))
        gates['G19'].update(value=fall, status='measured', **{'pass': fall['pass']})
        gates['G1']['value']['Throw'] = record['throw']['game_metrics']['dihedral_over_30_share']
        gates['G1']['pass'] &= gates['G1']['value']['Throw'] <= .09
        boundary = record['throw']['reduction']['boundary_hausdorff_upper_m']
        gates['G32']['value']['Throw'] = boundary
        gates['G32']['pass'] &= boundary <= .0015
    return {'gates': gates, 'pass': all(g['pass'] for g in gates.values()),
            'simulation_seconds': {n: d['simulation']['elapsed_s'] for n, d in record['cushions'].items()}}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = measure(a.out)
    (a.out/'geometry-gates.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
