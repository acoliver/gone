"""#130: exported lower ribbon loops clear the fixed suspension and frozen wool."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

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
    lower = local[local[:,2] < .0216]
    assert report['loop_wrap_degrees'] >= 180
    assert report['folded_tongues'] == 2
    assert not crossing_pairs(medal), 'Metal, ribbon and self surfaces must not cross'
    assert not crossing_pairs(ribbon, bpy.data.objects['TunicBody'])
    assert np.ptp(local[:,0]) > .021, 'Full sewn ribbon width retained'
    assert lower[:,1].min() <= -.00359 and lower[:,1].max() >= -.00041, 'Both sides of 0.8 mm U-fold remain geometric'
    assert abs(lower[:,2].min()-.01725) < 1e-7, 'Measured lower turn around the bar'
    turn = lower[lower[:,2] < .020,0]
    slot_width = turn[turn > 0].min()-turn[turn < 0].max()
    assert slot_width >= .006, 'Measured central ring/claw relief remains open'
    assert set(ribbon.data.uv_layers.keys()) == {'DetailUV','BakeUV'}
    assert 'RibbonColours' in ribbon.data.color_attributes
print('PASS: measured lower ribbon folds, full upper width, open ring relief, zero self/metal/cloth crossings')
