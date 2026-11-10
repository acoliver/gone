"""Grain branches remain deterministic and survive saved-image reload."""
from pathlib import Path
import json
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from tear_opacity import wool_opacity

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/tunic6/main/baked.blend'))
body = bpy.data.objects['TunicBody']
out = ROOT/'tmp/age/tunic7/controls/grain-opacity.png'
image, report = wool_opacity(body, out)
assert report['changed_texels'] > 0
assert report['transparent_texels'] > 0
out.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
assert len(report['grain_paths_m']) == 4
for path in report['grain_paths_m']:
    delta = np.diff(path, axis=0)
    angles = np.arctan2(delta[:, 1], delta[:, 0])
    deviation = np.abs((angles+np.pi/4) % (np.pi/2)-np.pi/4)
    assert deviation.max() <= np.pi/15+1e-7
    assert np.linalg.norm(delta, axis=1).max() <= .0050001
before = np.array(image.pixels[:])
image.reload()
np.testing.assert_array_equal(before, image.pixels[:])
print('PASS: 30 mm grain walks, 18 mm branches, physical lip distances and saved alpha')
