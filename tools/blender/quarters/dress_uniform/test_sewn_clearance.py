"""Background Blender control: collar layering follows its sewn support normal."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import follow_points

mesh = bpy.data.meshes.new('Upright sewn patch')
mesh.from_pydata([(0, 0, 0), (0, 1, 0), (0, 0, 1)], [], [(0, 1, 2)])
obj = bpy.data.objects.new(mesh.name, mesh)
bpy.context.collection.objects.link(obj)
entry = dict(triangle=[0, 1, 2], weights=[1., 0., 0.], offset=[0., 0., .043], sewn_clearance_m=.002)
point = follow_points(obj, [entry])[0]
np.testing.assert_allclose(point, [.002, 0., .043], atol=1e-8)
obj.location = (.1, -.2, -.025)
translated = follow_points(obj, [entry])[0]
bpy.context.view_layer.update()
translated = follow_points(obj, [entry])[0]
np.testing.assert_allclose(translated-point, [.1, -.2, -.025], atol=1e-8)
print('PASS: 2 mm sewn layering follows the support normal, with no world-Z lift', flush=True)
