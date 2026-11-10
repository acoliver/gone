"""A deformed facing must not exchange its inner and outer vertex identities."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from detail_clearance import seat_sewn


def mesh(name, vertices, faces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


bpy.ops.wm.read_factory_settings(use_empty=True)
body = mesh('TunicBody', [(-.1, -.1, 0), (.1, -.1, 0), (.1, .1, 0), (-.1, .1, 0)],
            [(0, 1, 2, 3)])
base = np.array([[-.01, -.01, .001], [.01, -.01, .001],
                 [.01, .01, .001], [-.01, .01, .001]])
original = np.vstack([base, base+[0, 0, .0006]])
posed = original.copy()
posed[[0, 4]] = posed[[4, 0]]
bindings = {}
for name in ('ShoulderBoard_L', 'ShoulderBoard_R', 'Placket', 'RibbonBar'):
    mesh(name, posed, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                       (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    bindings[name] = dict(original=original.tolist(),
                         entries=[dict(offset_frame=np.eye(3).tolist()) for _ in original])
seat_sewn(body, bindings)
for name in bindings:
    points = np.array([v.co[:] for v in bpy.data.objects[name].data.vertices])
    np.testing.assert_allclose(points[:4, 2], .0005, atol=1e-8)
    np.testing.assert_allclose(points[4:, 2], .0011, atol=1e-8)
print('PASS: facing inner/outer identities come from the source, not distorted pose')
