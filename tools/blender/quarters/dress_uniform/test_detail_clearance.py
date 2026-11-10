"""A fitting must clear support triangles even when no support vertex is below it."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from detail_clearance import seat_details
from fabric_mesh import material, new_object
from triangle_contacts import intersect

bpy.ops.wm.read_factory_settings(use_empty=True)
body = new_object('TunicBody', [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)],
                  [(0, 1, 2), (0, 2, 3)], material('Wool', (.025, .043, .08)))
bpy.ops.mesh.primitive_cube_add(size=1)
detail = bpy.context.object
detail.name = 'RibbonBar'
detail.scale = (.05, .002, .02)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
original = np.array([v.co[:] for v in detail.data.vertices])
binding = dict(original=original.tolist(), rigid=True, groups=[list(range(len(original)))])
seat_details(body, {'RibbonBar': binding})
body.data.calc_loop_triangles()
detail.data.calc_loop_triangles()
a = np.array([body.matrix_world @ v.co for v in body.data.vertices])
b = np.array([detail.matrix_world @ v.co for v in detail.data.vertices])
assert max(b[:, 1]) <= -.0005+1e-7
for first in body.data.loop_triangles:
    for second in detail.data.loop_triangles:
        assert not intersect(a[list(first.vertices)], b[list(second.vertices)])
assert np.max(np.ptp((b-original), axis=0)) < 1e-7
print('PASS: rigid fitting clears an intersecting large support triangle without warping', flush=True)
