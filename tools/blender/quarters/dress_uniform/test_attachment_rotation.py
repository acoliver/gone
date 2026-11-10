"""Attachment offsets must rotate with the supporting wool triangle."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import bind_points, follow_points

mesh = bpy.data.meshes.new('Support rotation')
mesh.from_pydata([(0, 0, 0), (.1, 0, 0), (0, .1, 0)], [], [(0, 1, 2)])
obj = bpy.data.objects.new(mesh.name, mesh)
bpy.context.collection.objects.link(obj)
entries = bind_points(obj, [[.03, .03, .01]])
for vertex in mesh.vertices:
    x, y, z = vertex.co
    vertex.co = (x, -z, y)
mesh.update()
np.testing.assert_allclose(follow_points(obj, entries), [[.03, -.01, .03]], atol=1e-7)
print('PASS: attachment offset follows support rotation without detaching')
