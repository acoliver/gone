"""Rigid medal bases need a pressed wool support, not a fit to their full volume."""
from pathlib import Path
import json
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from detail_clearance import seat_medal, press_medal_support
from fabric_mesh import material, new_object
from reduced_clearance import crossing_pairs

bpy.ops.wm.read_factory_settings(use_empty=True)
mat = material('Control', (.1, .1, .1))
v = [(x, .008*(x/.05)**2, z) for z in np.linspace(-.05, .05, 13) for x in np.linspace(-.05, .05, 13)]
f = [(j*13+i, (j+1)*13+i, (j+1)*13+i+1, j*13+i+1) for j in range(12) for i in range(12)]
body = new_object('TunicBody', v, f, mat)
base = np.array([[-.025, -.001, -.025], [.025, -.001, -.025],
                 [.025, -.001, .025], [-.025, -.001, .025]])
original = np.vstack([base, base+[0, -.002, 0]])
faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
obj = new_object('Medal', original, faces, mat)
obj['attachment'] = json.dumps({'base_blender_m': base.tolist()})
new_object('RibbonBar', [(1, 0, 0), (1.01, 0, 0), (1, 0, .01)], [(0, 1, 2)], mat)
binding = dict(original=original.tolist(), groups=[list(range(8))])
first = seat_medal(body, binding)
assert not first[0]['within_2mm'], first
pressed = press_medal_support(body, binding)
assert pressed['maximum_motion_m'] <= .0015001
final = seat_medal(body, binding)
assert final[0]['within_2mm'], final
points = np.array([v.co[:] for v in obj.data.vertices])
np.testing.assert_allclose(np.linalg.norm(points[:, None]-points[None, :], axis=2),
                           np.linalg.norm(original[:, None]-original[None, :], axis=2), atol=1e-7)
assert not crossing_pairs(obj, body)
print('PASS: rigid medal clears wool and all authored base anchors seat within 2 mm', first, final)
