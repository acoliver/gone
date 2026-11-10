"""A torn allowance remains part of the sheet, rather than a floating trim strip."""
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from common import assert_surface_clear
from fabric_mesh import material, new_object
from torn_allowance import add_allowances

bpy.ops.wm.read_factory_settings(use_empty=True)
points = [(.15, -.01, -.22), (.25, -.01, -.22), (.25, -.01, -.32), (.15, -.01, -.32),
          (.285, -.01, -.26), (.325, -.01, -.26), (.325, -.01, -.45), (.285, -.01, -.45)]
body = new_object('Allowance control', points, [(0, 1, 2, 3), (4, 5, 6, 7)],
                  material('Wool', (.025, .043, .08)))
patterns = [[(.36, .9), (.46, .9), (.46, .7), (.36, .7)],
            [(1.1, 0), (1.55, 0), (1.55, .4), (1.1, .4)]]
pattern = [uv for face in patterns for uv in face]
for loop in body.data.loops:
    body.data.uv_layers.active.data[loop.index].uv = pattern[loop.vertex_index]
report = add_allowances(body)
assert report['extended_vertices'] > 30
assert .00025 <= report['minimum_maximum_width_m'][0]
assert report['minimum_maximum_width_m'][1] <= .0110001
assert np.isfinite(np.array([v.co[:] for v in body.data.vertices])).all()
bm = bmesh.new()
bm.from_mesh(body.data)
assert all(edge.is_manifold or edge.is_boundary for edge in bm.edges)
remaining = set(bm.verts)
components = 0
while remaining:
    pending = [remaining.pop()]
    while pending:
        vertex = pending.pop()
        for edge in vertex.link_edges:
            other = edge.other_vert(vertex)
            if other in remaining:
                remaining.remove(other)
                pending.append(other)
    components += 1
bm.free()
assert components == 2, f'Extrusion detached {components-2} pieces from the two input sheets'
assert_surface_clear(body)
print('PASS: curved allowance lips stay connected, finite and crossing-free', report)

from torn_allowance import ragged_shoulders
shoulder = new_object('Shoulder control', [(.14, -.01, -.20), (.25, -.01, -.20),
                                           (.25, -.01, -.25), (.14, -.01, -.25)],
                       [(0, 1, 2, 3)], material('Shoulder wool', (.025, .043, .08)))
pattern = [(.3, .94), (.46, .94), (.46, .86), (.3, .86)]
for loop in shoulder.data.loops:
    shoulder.data.uv_layers.active.data[loop.index].uv = pattern[loop.vertex_index]
group = shoulder.vertex_groups.new(name='Lip shrink')
group.add([0, 1, 2, 3], 1., 'REPLACE')
shoulder_report = ragged_shoulders(shoulder)
assert shoulder_report['maximum_lip_loss_m'] > .002
assert shoulder_report['maximum_lip_loss_m'] <= .008
assert shoulder_report['moved_vertices'] > 20
assert_surface_clear(shoulder)
print('PASS: physically ragged shoulder lips remain a connected crossing-free sheet', shoulder_report)
