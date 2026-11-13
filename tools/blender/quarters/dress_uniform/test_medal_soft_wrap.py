"""#130 generated-size ring and rounded fabric bend over the bar."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tunic_details import extract_ribbon, points

sources = Path(sys.argv[sys.argv.index('--sources')+1]) if '--sources' in sys.argv else HERE
for state in ['working','pilot']:
    bpy.ops.wm.open_mainfile(filepath=str(sources/f'tunic-{state}.blend'))
    medal = bpy.data.objects['Medal']
    eyelet = json.loads(medal['eyelet'])
    assert eyelet['uniform_ring_scale'] == 1., 'Return to the original generated ring size'
    assert eyelet['suspender_loop']['radius_m'] < .0045
    assert eyelet['suspender_loop']['wire_radius_m'] in [.0004,.00045]
    record = json.loads(medal['ribbon_loop'])
    path, normals = np.array(record['wrap_centerline_m']), np.array(record['wrap_normals'])
    np.testing.assert_allclose(np.linalg.norm(normals,axis=1),1,atol=1e-12)
    # The two quarter arcs join the rising front, top and returning rear tangentially.
    controls = np.array(record['approach_controls_m'])
    direction = controls[-1]-controls[-2]
    np.testing.assert_allclose(direction/np.linalg.norm(direction),[0,1],atol=1e-12)
    bounds = np.array(eyelet['bar_bounds_m'])
    radius = record['bend_radius_m']
    assert radius-.0004 >= .00008
    np.testing.assert_allclose(path[7],[bounds[0,1]-radius,bounds[1,2]],atol=1e-12)
    np.testing.assert_allclose(normals[7],[1,0],atol=1e-12)
    np.testing.assert_allclose(normals[12:14],[[0,-1],[0,-1]],atol=1e-12)
    np.testing.assert_allclose(normals[18:],np.tile([-1,0],(4,1)),atol=1e-12)
    frame = json.loads(medal['medal_frame'])
    ribbon = extract_ribbon(medal)
    local = (points(ribbon)-np.array(frame['origin'])) @ np.array(frame['frame']).T
    for row in range(22):
        a,b = local[64+row*14:71+row*14],local[71+row*14:78+row*14]
        np.testing.assert_allclose((a[:,1:]+b[:,1:])/2,np.tile(path[row],(7,1)),atol=6e-8)
        np.testing.assert_allclose(a[:,1:]-b[:,1:],np.tile(normals[row]*.0008,(7,1)),atol=6e-8)
print('PASS: generated-size ring and measured 0.8 mm tangent-continuous rounded fabric wrap')
