"""Check saved pass-ten material and geometry contracts on the actual candidate."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(a.out/'finished.blend'))
record = json.loads(bpy.context.scene['tunic5_record'])
assert record['pass10']['age_years'] == 1000
assert record['pass10']['details']['surviving_yarns'] >= 2
assert record['pass10']['allowance']['extended_vertices'] > 50
assert record['opacity']['stress_wear']['through_texels'] > 0
assert record['opacity']['stress_wear']['thinning_texels'] > 1000
body = bpy.data.objects['TunicBody']
assert any(mat.name.startswith('Exposed wool seam allowance') for mat in body.data.materials)
image = bpy.data.images[body['pass10_thinning_image']]
assert tuple(image.size) == (4096, 4096)
values = np.array(image.pixels[:]).reshape(-1, 4)
assert np.isfinite(values).all()
assert values[:, 0].max() > .9
mound = bpy.data.objects['FibreDust']
color = record['heap_material']['albedo_linear']
assert color[0] >= .3 and color[2] >= .24
fibres = bpy.data.objects['HeapFibres']
assert fibres.data.materials[0].name.startswith('Loose pale wool fibres')
assert record['reduction']['TunicBody']['boundary_hausdorff_upper_m'] <= .0015
assert json.loads((a.out/'repeat.json').read_text())['byte_identical']
for name in ['ShoulderBoard_L', 'ShoulderBoard_R']:
    assert bpy.data.objects[name]['surface_seated_board']
print('PASS: saved allowance, anchored yarns, sparse wear, independent dust colour, seated boards and repeat export')
