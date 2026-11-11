"""#130: a full-width ribbon threads a closed slot above the separate ring lug."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tunic_details import extract_ribbon, points
from reduced_clearance import crossing_pairs

for name in ['working', 'pilot']:
    bpy.ops.wm.open_mainfile(filepath=str(HERE / f'tunic-{name}.blend'))
    medal = bpy.data.objects['Medal']
    report = json.loads(medal['ribbon_loop'])
    record = json.loads(medal['medal_frame'])
    origin, frame = np.array(record['origin']), np.array(record['frame'])
    ribbon = extract_ribbon(medal)
    local = np.einsum('ij,kj->ik', points(ribbon)-origin, frame)
    assert report['loop_wrap_degrees'] >= 180
    assert report['folded_tongues'] == 1 and report['full_width']
    assert report['ring_lug_separate_from_ribbon']
    assert report['slot_height_m'] >= .0008 + 2*.00008
    assert report['slot_width_m'] >= .0219 + 2*.00008
    assert not crossing_pairs(medal), 'Metal, ribbon and self surfaces must not cross'
    assert not crossing_pairs(ribbon, bpy.data.objects['TunicBody'])
    ribbon.data.calc_loop_triangles()
    tree = BVHTree.FromPolygons(local.tolist(), [t.vertices[:] for t in ribbon.data.loop_triangles], all_triangles=True)
    # A former split-tab or central-slot ribbon cannot hit the front loop at every station.
    for x in np.linspace(-.010, .010, 81):
        hit = tree.ray_cast(Vector((x, -.02, .0243)), Vector((0, 1, 0)), .04)[0]
        assert hit is not None and hit.y < -.0035, ('Missing full-width front fold', x, hit)
    assert np.ptp(local[:, 0]) > .021, 'Full sewn ribbon width retained'
    assert set(ribbon.data.uv_layers.keys()) == {'DetailUV', 'BakeUV'}
    assert 'RibbonColours' in ribbon.data.color_attributes
print('PASS: closed-slot full-width ribbon loop, separate lug, zero self/metal/cloth crossings')
