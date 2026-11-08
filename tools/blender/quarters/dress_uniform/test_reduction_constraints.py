"""Background Blender controls for bounded game-mesh relaxation."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'quarters_aging'))
from reduction_constraints import relax_interior
from fabric_mesh import new_object

vertices = [(x*.01, y*.01, .02 if x == y == 2 else 0.) for y in range(5) for x in range(5)]
faces = [(y*5+x, y*5+x+1, (y+1)*5+x+1, (y+1)*5+x) for y in range(4) for x in range(4)]
obj = new_object('Relaxation control', vertices, faces, None)
keep = obj.vertex_groups.new(name='Keep')
keep.add([6], 1., 'REPLACE')
original = np.array([v.co[:] for v in obj.data.vertices])
report = relax_interior(obj)
actual = np.array([v.co[:] for v in obj.data.vertices])
movement = np.linalg.norm(actual-original, axis=1)
assert movement.max() <= .00100001, movement.max()
assert movement[12] > .0009, 'Control must actually exercise the displacement cap'
assert movement[6] == 0., 'Keep weights must also protect relaxation'
boundary = [y*5+x for y in range(5) for x in range(5) if x in [0, 4] or y in [0, 4]]
assert (movement[boundary] == 0.).all(), 'Open lips moved during relaxation'
assert report['keep_fixed'] and report['boundary_fixed']
print('PASS: lips and Keep stay fixed; interior displacement is bounded to 1 mm', flush=True)
