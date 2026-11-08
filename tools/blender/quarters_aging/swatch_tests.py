"""Measure a 200 mm cantilever swatch before and after a zero-area slit."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth_stage import configure, simulate
from fabric_mesh import material, new_object
from tear_paths import split_polyline

ROOT = Path(__file__).resolve().parents[3]


def swatch(edge, fabric, split, frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    n = int(np.ceil(.2/edge))
    vertices = [(x*.2/n, y*.2/n, .25) for y in range(n+1) for x in range(n+1)]
    faces = [(y*(n+1)+x, y*(n+1)+x+1, (y+1)*(n+1)+x+1, (y+1)*(n+1)+x)
             for y in range(n) for x in range(n)]
    obj = new_object('Swatch', vertices, faces, material('Swatch material', (.3, .3, .3)))
    reference_count = 10**2  # 9 cells, matching the 24 mm reference swatch.
    cut = None
    if split:
        cut = split_polyline(obj, [(.06, .09, .25), (.1, .09, .25), (.1, .13, .25), (.14, .13, .25)])
    initial = np.array([v.co[:] for v in obj.data.vertices])
    tips = np.flatnonzero(initial[:, 1] > .1999)
    duplicates = {}
    for i, point in enumerate(initial):
        duplicates.setdefault(tuple(np.round(point, 7)), []).append(i)
    pairs = [ids for ids in duplicates.values() if len(ids) == 2]
    pins = {v.index: 1. for v in obj.data.vertices if v.co.y < .00001}
    config = {'mass': .025 if fabric == 'upholstery' else .15,
              'stiffness': 180 if fabric == 'upholstery' else 150,
              'bending': .2 if fabric == 'upholstery' else .5,
              'shrink': .04, 'frames': frames}
    mod = configure(obj, config, reference_count, pins)
    mass = mod.settings.mass
    result = simulate(obj, mod, frames)
    p = np.array([v.co[:] for v in obj.data.vertices])
    tip = p[tips]
    result.update(fabric=fabric, requested_edge_m=edge, actual_edge_m=.2/n,
                  vertices=len(p), split=split, cut=cut, settings=config,
                  vertex_mass_kg=mass, total_mass_kg=mass*len(p),
                  tip_drop_m=float(.25-tip[:, 2].mean()),
                  z_quantiles_m=np.quantile(p[:, 2], [.1, .5, .9]).tolist())
    # Gap is measured between duplicated slit vertices in the final simulation.
    if split:
        gaps = [float(np.linalg.norm(p[a]-p[b])) for a, b in pairs]
        lifts = []
        for index in [i for pair in pairs for i in pair]:
            distances = np.linalg.norm(initial-initial[index], axis=1)
            neighbours = p[(distances >= .009) & (distances <= .020)]
            if len(neighbours) >= 3:
                centre = neighbours.mean(0)
                normal = np.linalg.svd(neighbours-centre)[2][-1]
                lifts.append(float(abs((p[index]-centre)@normal)))
        result['split_gaps_m'] = gaps
        result['lip_plane_distances_m'] = lifts
        result['lip_lift_over_3mm_fraction'] = float(np.mean(np.array(lifts) > .003)) if lifts else None
        result['lip_calibration_status'] = 'measured against local 9..20 mm plane; not accepted automatically'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass4/swatches')
    p.add_argument('--frames', type=int, default=150)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    results = []
    for fabric in ['upholstery', 'wool']:
        reference = swatch(.024, fabric, False, a.frames)
        results.append(reference)
        for edge in [.006, .003]:
            uncut = swatch(edge, fabric, False, a.frames)
            error = abs(uncut['tip_drop_m']-reference['tip_drop_m'])
            uncut['reference_tip_drop_m'] = reference['tip_drop_m']
            uncut['drape_error_m'] = error
            uncut['drape_match'] = error <= .01
            results.append(uncut)
            results.append(swatch(edge, fabric, True, a.frames))
            (a.out/'measurements.json').write_text(json.dumps(results, indent=2)+'\n')
    trials = ROOT/'tools/blender/quarters/sofa/cloth-trials.json'
    record = json.loads(trials.read_text())
    record['pass4_swatches'] = {'frames': a.frames, 'results': results,
                                'calibrated': False, 'reason': 'Lip curl and split gape require measurement before production settings are accepted'}
    trials.write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    main()
