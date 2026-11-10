"""Empirical 200 mm swatch calibration; retain every sampled setting and profile."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth_stage import configure, simulate
from fabric_mesh import material, new_object

ROOT = Path(__file__).resolve().parents[3]


def references():
    trials = json.loads((ROOT/'tools/blender/quarters/sofa/cloth-trials.json').read_text())
    selected = trials['selected']['cushion']
    seat = next(t['settings'] for t in trials['followup']['cushion_trials']
                if t['settings']['name'] == selected)
    return {'upholstery': {'stiffness': seat['stiffness'], 'shear': seat['shear_stiffness'],
                           'bending': seat['bending'], 'mass': seat['mass'],
                           'source': 'selected fitted cushion '+selected},
            'wool': {'stiffness': 150., 'shear': 80., 'bending': .25, 'mass': .15,
                     'source': 'fitted throw reference: bending 0.25 confirmed in #95 brief; structural/mass from throw-l'}}


def trial(edge, reference, factors, frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24
    n = int(np.ceil(.2/edge))
    vertices = [(x*.2/n, y*.2/n, .25) for y in range(n+1) for x in range(n+1)]
    faces = [(y*(n+1)+x, y*(n+1)+x+1, (y+1)*(n+1)+x+1, (y+1)*(n+1)+x)
             for y in range(n) for x in range(n)]
    obj = new_object('Calibration', vertices, faces, material('Cloth', (.3, .3, .3)))
    pins = {v.index: 1. for v in obj.data.vertices if v.co.y < .00001}
    config = {key: reference[key]*factors.get(key, 1.) for key in ['mass', 'stiffness', 'bending', 'shear']}
    config.update(frames=frames, quality=12, damping_factor=factors.get('damping', 1.),
                  air_factor=factors.get('air', 1.))
    mod = configure(obj, config, 100, pins)
    simulation = simulate(obj, mod, frames)
    p = np.array([v.co[:] for v in obj.data.vertices]).reshape(n+1, n+1, 3).mean(1)
    stations = np.linspace(0, .2, 21)
    profile = np.array([np.interp(stations, np.linspace(0, .2, n+1), p[:, axis]) for axis in range(3)]).T
    return {'edge_m': .2/n, 'factors': factors, 'settings': config,
            'tip_drop_m': float(.25-p[-1, 2]), 'profile_m': profile.tolist(),
            'total_mass_kg': simulation['vertex_mass_kg']*len(vertices),
            'elapsed_s': simulation['elapsed_s']}


def select(samples):
    # Within tolerance, preserve areal mass before minimizing the residual.
    return min(samples, key=lambda s: (not s['pass'],
               abs(np.log(s['factors'].get('mass', 1.))), s['profile_error_max_m']))


def calibrate(out, frames):
    out.mkdir(parents=True, exist_ok=True)
    record = {'fixture': '200 mm cantilever, 21 width-averaged material stations, 24 fps',
              'frames': frames, 'references': references(), 'fabrics': {}}
    def save():
        (out/'calibration.json').write_text(json.dumps(record, indent=2)+'\n')
    for fabric, ref in record['references'].items():
        baseline = trial(.024, ref, {}, frames)
        data = {'reference': baseline, 'samples': []}
        record['fabrics'][fabric] = data
        def sample(factors):
            result = trial(.006, ref, factors, frames)
            distances = np.linalg.norm(np.array(result['profile_m'])-baseline['profile_m'], axis=1)
            result['profile_error_max_m'] = float(distances.max())
            result['profile_error_rms_m'] = float(np.sqrt(np.mean(distances**2)))
            result['tip_error_m'] = abs(result['tip_drop_m']-baseline['tip_drop_m'])
            result['pass'] = result['profile_error_max_m'] <= .010
            data['samples'].append(result)
            save()
            print('CALIBRATION', fabric, factors, result['profile_error_max_m'], flush=True)
            return result
        # Keep spring-only controls before fitting resolution-dependent damping.
        samples = [sample({'bending': b, 'stiffness': b, 'shear': b})
                   for b in [.0001, .0004, .0016, .0064, .0256, .1, .4, 1.]]
        best = min(samples, key=lambda s: s['profile_error_max_m'])
        for key in ['stiffness', 'mass']:
            factors = best['factors'].copy()
            samples = [best]
            for value in [.5, 2.]:
                f = {**factors, key: value}
                if key == 'stiffness':
                    f['shear'] = value
                samples.append(sample(f))
            best = min(samples, key=lambda s: s['profile_error_max_m'])
        # Resolve the remaining log-bending interval, retaining mass conservation
        # when it already gives the best match.
        for multiplier in [.75, 1.25]:
            f = {**best['factors'], 'bending': best['factors']['bending']*multiplier}
            samples.append(sample(f))
        grid = ([(d, s) for d in [.05, .08, .12] for s in [.05, .1, .16]]
                if fabric == 'upholstery' else [(d, s) for d in [.08, .12] for s in [.5, 1.]])
        for damping, spring in grid:
            sample({'damping': damping, 'air': damping, 'stiffness': spring,
                    'shear': spring, 'bending': spring})
        best = min(data['samples'], key=lambda s: s['profile_error_max_m'])
        for key in ['mass', 'stiffness', 'bending']:
            for factor in [.5, 2.]:
                sample({**best['factors'], key: best['factors'].get(key, 1.)*factor})
        best = select(data['samples'])
        data['selected'] = best
        ratio = best['edge_m']/baseline['edge_m']
        data['empirical_exponents'] = {k: float(np.log(best['factors'].get(k, 1.))/np.log(ratio))
                                       for k in ['stiffness', 'shear', 'bending', 'mass', 'damping', 'air']}
        save()
    record['pass'] = all(d['selected']['pass'] for d in record['fabrics'].values())
    save()
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass5/calibration')
    p.add_argument('--frames', type=int, default=150)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    calibrate(a.out, a.frames)
