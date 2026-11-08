"""Match dense 200 mm tunic-wool cantilevers to the fitted body-p material."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import HERE, ROOT
from cloth_stage import configure, simulate
from fabric_mesh import material, new_object


def reference():
    data = json.loads((HERE / 'cloth-trials.json').read_text())
    settings = next(t['settings'] for t in data['body'] if t['trial'] == 'body-p')
    tension, compression, shear = settings['tension_compression_shear']
    assert tension == compression
    return dict(stiffness=tension, shear=shear, bending=settings['bending'],
                mass=settings['mass_setting'], structural_damping=settings['structural_damping'],
                bending_damping=settings['bending_damping'], air_damping=settings['air_damping'],
                time_scale=settings['time_scale'])


def swatch(edge, ref, frames, damping):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24
    n = int(np.ceil(.2/edge))
    vertices = [(x*.2/n, y*.2/n, .25) for y in range(n+1) for x in range(n+1)]
    faces = [(y*(n+1)+x, y*(n+1)+x+1, (y+1)*(n+1)+x+1, (y+1)*(n+1)+x)
             for y in range(n) for x in range(n)]
    obj = new_object('TunicWoolSwatch', vertices, faces, material('Wool', (.025, .043, .08)))
    pins = {v.index: 1. for v in obj.data.vertices if v.co.y < 1e-5}
    config = {**ref, 'frames': frames, 'quality': 12}
    mod = configure(obj, config, 100, pins)
    s = mod.settings
    s.tension_damping = s.compression_damping = s.shear_damping = ref['structural_damping']*damping
    s.bending_damping = ref['bending_damping']*damping
    s.air_damping = ref['air_damping']*damping
    simulation = simulate(obj, mod, frames)
    profile = np.array([v.co[:] for v in obj.data.vertices]).reshape(n+1, n+1, 3).mean(1)
    stations = np.linspace(0, .2, 21)
    profile = np.array([np.interp(stations, np.linspace(0, .2, n+1), profile[:, axis])
                        for axis in range(3)]).T
    return dict(requested_edge_m=edge, edge_m=.2/n, vertices=len(vertices),
                total_mass_kg=simulation['vertex_mass_kg']*len(vertices),
                settings={**config, 'damping_multiplier': damping}, profile_m=profile.tolist(),
                seconds_per_frame=simulation['seconds_per_frame'],
                elapsed_s=simulation['elapsed_s'], tip_drop_m=float(.25-profile[-1, 2]))


def calibrate(out, frames):
    out.mkdir(parents=True, exist_ok=True)
    ref = reference()
    record = dict(fixture='200 x 200 mm cantilever; 21 width-averaged 3D stations; 24 fps',
                  source='unaged body-p', reference_settings=ref, frames=frames, samples=[])
    path = out / 'calibration.json'
    def save():
        path.write_text(json.dumps(record, indent=2)+'\n')
    baseline = swatch(.024, ref, frames, 1.)
    record['reference'] = baseline
    save()
    for edge in [.006, .003]:
        ratio = (.2/np.ceil(.2/edge))/baseline['edge_m']
        for damping in [ratio**1.595219466, 1.]:
            result = swatch(edge, ref, frames, damping)
            distance = np.linalg.norm(np.array(result['profile_m'])-baseline['profile_m'], axis=1)
            result.update(profile_error_max_m=float(distance.max()),
                          profile_error_rms_m=float(np.sqrt(np.mean(distance**2))),
                          pass_drape=bool(distance.max() <= .010))
            record['samples'].append(result)
            save()
            print('TUNIC CALIBRATION', edge, damping, result['profile_error_max_m'], flush=True)
            if result['pass_drape']:
                break
    record['selected'] = {str(edge): min((s for s in record['samples'] if s['requested_edge_m'] == edge),
                                         key=lambda s: s['profile_error_max_m']) for edge in [.006, .003]}
    record['pass'] = all(s['pass_drape'] for s in record['selected'].values())
    save()
    if not record['pass']:
        raise SystemExit('Tunic swatch calibration failed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT / 'tmp/age/tunic5/calibration')
    p.add_argument('--frames', type=int, default=600)
    args = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    calibrate(args.out, args.frames)
