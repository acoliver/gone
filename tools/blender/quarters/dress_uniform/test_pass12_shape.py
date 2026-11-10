"""The hem cuts form unbranched lips and new debris is mass-accounted on the floor."""
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fringe_boundary import boundary_chains
from aging_cards import edge_groups
import json

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/tunic12/retained')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out = args.out
bpy.ops.wm.open_mainfile(filepath=str(out/'baked.blend'))
r = json.loads(bpy.context.scene['tunic5_record'])
body = bpy.data.objects['TunicBody']
for name in edge_groups(body):
    boundary_chains(body, name)
assert r['pass12']['hem']['maximum_tongue_relaxation_m'] > .025
assert r['pass12']['hem']['removed_area_m2'] > .004
assert r['lip_lift']['fraction'] >= .30
assert len(r['fallen']) == 6
mound = bpy.data.objects['FibreDust']
height = max((mound.matrix_world @ v.co).z for v in mound.data.vertices)+.95
assert .029 <= height <= .035, height
heap = r['pass12']['heap']
np.testing.assert_allclose(heap['hem_loss_to_fallen_area_m2']+heap['hem_loss_to_fibre_dust_area_m2'],
                           r['pass12']['hem']['removed_area_m2'], atol=1e-12)
for piece in r['fallen'][3:]:
    obj = bpy.data.objects[piece['name']]
    minimum = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    assert -.95 < minimum < -.947, (obj.name, minimum)
print('PASS: unbranched hem lips, longer tongues, lifted-lip fraction, floor seating, six fallen strips and conserved new-loss allocation')
