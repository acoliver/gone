"""Background Blender control: cut-edge thickness must not displace the baked sheet."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from aging_cards import rim_modifier
from common import apply
from fabric_mesh import material, new_object

original = np.array([(0, 0, 0), (.01, 0, 0), (.01, .01, 0), (0, .01, 0)])
obj = new_object('Rim control', original, [(0, 1, 2, 3)], material('Wool', (.025, .043, .08)))
apply(obj, rim_modifier(obj, []))
faces = [face for face in obj.data.polygons if face.material_index == 0]
assert len(faces) == 1, 'Rim-only Solidify must not duplicate the wool shell'
points = np.array([obj.data.vertices[i].co[:] for i in faces[0].vertices])
np.testing.assert_allclose(points, original, atol=1e-8,
                           err_msg='Solidify moved the baked surface and its collision support')
vertices = np.array([v.co[:] for v in obj.data.vertices])
assert abs(np.ptp(vertices[:, 2])-.003) < 1e-8
rims = [face for face in obj.data.polygons if face.material_index != 0]
assert len(rims) == 4
assert all(obj.data.materials[face.material_index].name.startswith('WoolCutEdge') for face in rims)
floor = new_object('Floor control', [(-1, -1, -.0025), (1, -1, -.0025),
                                    (1, 1, -.0025), (-1, 1, -.0025)], [(0, 1, 2, 3)], None)
resting = new_object('Resting wool', original, [(0, 1, 2, 3)], material('Wool on floor', (.025, .043, .08)))
apply(resting, rim_modifier(resting, [floor]))
lowest = min(v.co.z for v in resting.data.vertices)
assert lowest >= -.0023, f'The inward wool rim crossed its floor support: {lowest}'
print('PASS: unchanged baked sheet, one shell, 3 mm inward cut edge, WoolCutEdge material', flush=True)
