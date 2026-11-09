"""Fitting support faces survive panel simplification exactly."""
import sys
from pathlib import Path

import argparse
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from reduce_pass12 import reduce_body

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/tunic12/retained-planned')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(args.out/'baked.blend'))
body = bpy.data.objects['TunicBody_Dense']
patch = body.vertex_groups['DetailPatch'].index
protected = {v.index for v in body.data.vertices if any(g.group == patch and g.weight > 0 for g in v.groups)}


def key(obj, face):
    return frozenset(tuple(obj.data.vertices[i].co) for i in face.vertices)


supports = {key(body, face) for face in body.data.polygons if any(i in protected for i in face.vertices)}
original = {tuple(v.co) for v in body.data.vertices}
low, report = reduce_body(body, 7100)
assert supports <= {key(low, face) for face in low.data.polygons}
assert {tuple(v.co) for v in low.data.vertices} <= original
assert report['triangles'] <= 7100
assert report['boundary_hausdorff_upper_m'] <= .000126
print('PASS: exact support faces, no vertex motion, preserved boundary and the wool triangle budget')
