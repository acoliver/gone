"""Hem and cuff fringe use short curved ribbons and finer fractional-alpha fibres."""
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fabric_mesh import material, new_object
from fringe_boundary import spaced_cards
from soft_wool_atlas import bundle_alpha

fine = bundle_alpha(9521, fine=True)
wide = bundle_alpha(9521)
np.testing.assert_array_equal(fine, bundle_alpha(9521, fine=True))
assert np.isfinite(fine).all() and np.min(fine) == 0 and np.max(fine) == 1
assert fine.mean() < wide.mean()
assert np.sum((fine > 0) & (fine < 1)) > 1000
bpy.ops.wm.read_factory_settings(use_empty=True)
mat = material('Wool control', (.15, .16, .19))
obj = new_object('Hem control', [(0, 0, .1), (.2, 0, .1), (.2, .1, .1), (0, .1, .1)],
                 [(0, 1, 2, 3)], mat)
obj['pass11_wear'] = True
obj['pass12_wear'] = True
group = obj.vertex_groups.new(name='Hem fringe')
group.add(list(range(4)), 1., 'REPLACE')
fringe, report = spaced_cards(obj, mat, 9521, wool=True, blockers=[obj], group_name='Hem fringe', tuft_mat=mat.copy())
assert report['authored_coverage'] >= .70
assert report['triangles'] == report['cards']*4
assert report['extent_min_max_m'][1] <= .004501
assert all(p.material_index == 1 for p in fringe.data.polygons)
points = np.array([v.co[:] for v in fringe.data.vertices]).reshape(-1, 3, 2, 3)
assert np.max(np.ptp(points.mean(2)[:, :, 2], axis=1)) > .0001
print('PASS: finer deterministic fractional-alpha fibres, curved hem tufts and >=70% attached-root coverage')
