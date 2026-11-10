"""Two cut edges share the available ply gap instead of each consuming it."""
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from aging_cards import rim_modifier
from common import apply, recalc
from fabric_mesh import material
from triangle_contacts import intersect

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new('Opposing wool plies')
quad = [(-.02, -.02, 0), (.02, -.02, 0), (.02, .02, 0), (-.02, .02, 0)]
mesh.from_pydata(quad+[(x, y, .002) for x, y, _ in quad], [], [(3, 2, 1, 0), (4, 5, 6, 7)])
obj = bpy.data.objects.new(mesh.name, mesh)
bpy.context.collection.objects.link(obj)
mesh.materials.append(material('Wool separation control', (.025, .043, .08)))
recalc(obj)
apply(obj, rim_modifier(obj, []))
mesh.calc_loop_triangles()
vertices = np.array([vertex.co[:] for vertex in mesh.vertices])
faces = np.array([face.vertices[:] for face in mesh.loop_triangles])
tree = BVHTree.FromPolygons(vertices.tolist(), faces.tolist(), all_triangles=True)
contacts = []
for i, j in tree.overlap(tree):
    if i >= j or np.any(np.linalg.norm(vertices[faces[i]][:, None]-vertices[faces[j]][None, :], axis=2) < 1e-7):
        continue
    if intersect(vertices[faces[i]], vertices[faces[j]]):
        contacts.append((i, j))
assert not contacts, f'Opposing rims consumed the same clearance: {contacts}'
print('PASS: opposing wool rims retain a positive gap without moving either sheet')
