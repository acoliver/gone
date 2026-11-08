"""Reduce cut-residue templates and measure their exported flake geometry."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import decimate
from common import export, recalc, save
from fabric_mesh import material, new_object
from foam_collapse import largest_shell


def build(source, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    out.mkdir(parents=True, exist_ok=True)
    record = []
    for path in sorted(source.glob('fragment-*.npz')):
        data = np.load(path)
        dense = new_object(path.stem, data['vertices'], data['faces'], material('Foam', (.28, .19, .10)))
        dense['aged_export'] = False
        # A crumb is one connected skin piece, not the enclosed pore shells.
        largest_shell(dense)
        recalc(dense)
        low, reduction = decimate(dense, 24)
        recalc(low)
        points = np.array([v.co[:] for v in low.data.vertices])
        axes = np.linalg.svd(points-points.mean(0))[2]
        extents = np.sort(np.ptp(points@axes.T, axis=0))
        aspect = float(extents[0]/extents[-1])
        low.location.x = len(record)*.04
        entry = {'template': path.stem, 'source': str(path), 'reduction': reduction,
                 'thickness_width': aspect, 'pass': .25 <= aspect <= .7 and 14 <= reduction['triangles'] <= 40}
        low['aged_export'] = entry['pass']
        record.append(entry)
        bpy.data.objects.remove(dense, do_unlink=True)
        low.name = path.stem
    report = {'templates': record, 'passing_templates': sum(r['pass'] for r in record)}
    report['pass'] = report['passing_templates'] >= 8
    (out/'fragments.json').write_text(json.dumps(report, indent=2)+'\n')
    save(out/'fragment-library.blend', report)
    export(out/'fragment-library.glb')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    result = build(a.source, a.out)
    print(json.dumps(result, indent=2), flush=True)
    raise SystemExit(0 if result['pass'] else 1)
