"""A reduced triangle crossing its support must be pushed clear, not excluded."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fabric_mesh import material, new_object
from reduced_clearance import crossing_pairs, push_out, compress_rim

bpy.ops.wm.read_factory_settings(use_empty=True)
mat = material('Control', (.1, .1, .1))
support = new_object('Support', [(-.1, -.1, 0), (.1, -.1, 0), (0, .1, 0)], [(0, 1, 2)], mat)
cloth = new_object('Cloth', [(-.01, 0, -.0004), (.01, 0, .0002), (0, .01, .0002)], [(0, 1, 2)], mat)
assert crossing_pairs(cloth, support)
report = push_out(cloth, support)
assert report['crossings_after'] == 0, report
assert report['maximum_motion_m'] <= .003
assert min(v.co.z for v in cloth.data.vertices) >= .0004999
assert len(cloth.data.vertices) == 3 and len(cloth.data.polygons) == 1
print('PASS: strict SAT is zero after bounded push-out; no topology changes or exemptions', report)

base = np.array([[-.02, -.02, 0.], [.02, -.02, 0.], [0., .02, 0.]])
other = base+[.003, 0., .00015]
points = np.vstack([base, other, base+[0., 0., .003], other-[0., 0., .003]])
faces = [(0, 1, 2), (3, 4, 5), (6, 8, 7), (9, 11, 10)]
for start in (0, 3):
    for a, b in ((0, 1), (1, 2), (2, 0)):
        faces.append((start+a, start+b, start+b+6, start+a+6))
stack = new_object('Overpacked rims', points, faces, mat)
source = stack.data.attributes.new(name='Wool rim source', type='INT', domain='POINT')
source.data.foreach_set('value', np.tile(np.arange(6, dtype=np.int32), 2))
assert crossing_pairs(stack)
compression = compress_rim(stack, 6)
actual = np.array([v.co[:] for v in stack.data.vertices])
assert np.linalg.norm(actual[6:]-actual[:6], axis=1).min() >= .00009999
assert compression['remaining_crossings'] > 0, 'Compression must not hide overpacked rims at weld tolerance'
print('PASS: unresolved overpacking stays a failure; compressed rims retain finite thickness', compression)

from aging_cards import rim_modifier
from common import apply
points = [(x*.01, y*.01, 0.) for y in range(5) for x in range(5)]
faces = [(y*5+x, y*5+x+1, (y+1)*5+x+1, (y+1)*5+x) for y in range(4) for x in range(4)]
grid = new_object('Boundary-copy mapping', points, faces, mat)
apply(grid, rim_modifier(grid, []))
assert len(grid.data.vertices) == 41, 'Only sixteen boundary copies should be appended to 25 sheet vertices'
source = grid.data.attributes['Wool rim source'].data
assert any(source[i].value != i-25 for i in range(25, 41))
assert compress_rim(grid, 25)['remaining_crossings'] == 0
print('PASS: rim compression uses preserved source IDs for boundary-only copies')
