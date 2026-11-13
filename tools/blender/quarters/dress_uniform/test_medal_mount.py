"""#130: soldered generated hardware supports the full-width sewn ribbon."""
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
from medal_solder_checks import suspension_measurements

SOURCES = Path(sys.argv[sys.argv.index('--sources') + 1]) if '--sources' in sys.argv else HERE
suspension = {}
for name in ['working', 'pilot']:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCES / f'tunic-{name}.blend'))
    medal = bpy.data.objects['Medal']
    report = json.loads(medal['ribbon_loop'])
    record = json.loads(medal['medal_frame'])
    origin, frame = np.array(record['origin']), np.array(record['frame'])
    assert json.loads(medal['eyelet'])['construction'] == 'Generated ring soldered to lug; centred perpendicular loop unioned to bar front-lower edge'
    suspension[name] = suspension_measurements(medal)
    ribbon = extract_ribbon(medal)
    local = np.einsum('ij,kj->ik', points(ribbon) - origin, frame)
    assert report['loop_wrap_degrees'] >= 180
    assert report['folded_tongues'] == 1 and report['full_width']
    assert not report['ring_lug_separate_from_ribbon']
    assert report['slot_height_m'] == report['slot_width_m'] == 0
    assert json.loads(medal['eyelet'])['construction'] == 'Generated ring soldered to lug; centred perpendicular loop unioned to bar front-lower edge'
    assert report['minimum_design_clearance_m'] == .00008
    assert report['cloth_thickness_m'] == .0008
    assert not crossing_pairs(medal), 'Metal, ribbon and self surfaces must not cross'
    assert not crossing_pairs(ribbon, bpy.data.objects['TunicBody'])
    ribbon.data.calc_loop_triangles()
    tree = BVHTree.FromPolygons(local.tolist(), [t.vertices[:] for t in ribbon.data.loop_triangles], all_triangles=True)
    station = report['front_fold_station_m']
    for x in np.linspace(-.010, .010, 81) + station[0]:
        hit = tree.ray_cast(Vector((x, -.02, station[2])), Vector((0, 1, 0)), .04)[0]
        assert hit is not None and hit.y < station[1] + .0005, ('Missing full-width front fold', x, hit)
    assert suspension[name]['loop_through_ring_disc'] and suspension[name]['ring_through_loop_disc']
    assert np.ptp(local[64:, 0]) > .021, 'Full sewn ribbon width retained in the lower fold'
    assert set(ribbon.data.uv_layers.keys()) == {'DetailUV', 'BakeUV'}
    assert 'RibbonColours' in ribbon.data.color_attributes
print('SOLDERED_SUSPENSION', json.dumps(suspension), flush=True)
print('PASS: connected soldered body/ring, upper-opening bar bearing <= 0.1 mm, full-width fold, zero crossings')
