"""Short curled shoulder tufts retain attached roots and valid atlas orientation."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fabric_mesh import material, new_object
from fringe_boundary import spaced_cards

bpy.ops.wm.read_factory_settings(use_empty=True)
mat = material('Wool test', (.025, .043, .08))
plane = new_object('Cloth control', [(0, 0, .1), (.2, 0, .1), (.2, .1, .1), (0, .1, .1)],
                   [(0, 1, 2, 3)], mat)
group = plane.vertex_groups.new(name='Long wool fringe')
group.add(list(range(4)), 1., 'REPLACE')
_, old = spaced_cards(plane, mat, 9521, wool=True, blockers=[plane], group_name=group.name)
plane['pass11_wear'] = True
fringe, report = spaced_cards(plane, mat, 9521, wool=True, blockers=[plane],
                              group_name=group.name, tuft_mat=mat.copy())
assert all(p.material_index == 1 for p in fringe.data.polygons)
assert report['cards'] < old['cards'], (old, report)
assert .001999 <= report['extent_min_max_m'][0] <= report['extent_min_max_m'][1] <= .004501
assert report['triangles'] == report['cards']*6
assert report['authored_coverage'] >= .70
points = np.array([v.co[:] for v in fringe.data.vertices]).reshape(-1, 4, 2, 3)
centers = points.mean(2)
assert np.max(abs(centers[:, 1:3, 2]-centers[:, :1, 2])) > .0001
for poly in fringe.data.polygons:
    for i in poly.loop_indices:
        vertex = fringe.data.loops[i].vertex_index
        uv = fringe.data.uv_layers.active.data[i].uv
        assert uv.x == vertex % 2
print('PASS: fewer short curled wool tufts, tapered atlas and actual root coverage', report)
