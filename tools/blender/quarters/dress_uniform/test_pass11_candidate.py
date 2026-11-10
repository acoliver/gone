"""Check saved pass-eleven fading, floor fray and strict retained geometry contracts."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(args.out/'finished.blend'))
record = json.loads(bpy.context.scene['tunic5_record'])
assert record['pass11']['age_years'] == 1000
assert record['pass11']['lips']['retained_pass10']
assert record['pass11']['wool_motion_maximum_m'] <= .0025
body = bpy.data.objects['TunicBody']
fields = bpy.data.images[body['pass10_thinning_image']]
rgba = np.array(fields.pixels[:]).reshape(fields.size[1], fields.size[0], 4)
assert rgba[:, :, 0].max() > .9
assert .03 < rgba[:, :, 1].max() <= .351
assert np.mean(abs(rgba[:, :, 0]-rgba[:, :, 1])) > .02
assert len(record['fallen_opacity']) == 3
assert record['heap']['fallen_fray_area_m2'] > 0
assert abs(record['heap']['fallen_fray_area_m2']-sum(r['lost_area_m2'] for r in record['fallen_opacity'].values())) < 1e-12
for name in record['fallen_opacity']:
    sheet = bpy.data.objects[name]
    assert sheet.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Alpha'].is_linked
assert all(item['remaining_crossings'] == 0 for item in record['rim_contacts'].values())
assert json.loads((args.out/'repeat.json').read_text())['byte_identical']
print('PASS: independent fading and thinning, three frayed scraps, lost-fibre accounting, clear rims and repeat export')
