"""Fallen-edge erosion removes wool only near the perimeter and measures its area."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fabric_mesh import material, new_object
from fallen_wear import fray, lost_area
from fringe_cards import image_from_array

out = ROOT/'tmp/age/tunic11/fallen-control'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
mat = material('Wool control', (.045, .061, .085))
obj = new_object('Fallen control', [(0, 0, 0), (.1, 0, 0), (.1, .1, 0), (0, .1, 0)], [(0, 1, 2, 3)], mat)
obj.data.uv_layers.active.name = 'BakeUV'
for loop in obj.data.loops:
    p = obj.data.vertices[loop.vertex_index].co
    obj.data.uv_layers.active.data[loop.index].uv = (p.x/.1, p.y/.1)
for value, expected in [(0., .01), (1., 0.)]:
    rgba = np.ones((128, 128, 4), np.float32)
    rgba[:, :, :3] = value
    image = image_from_array('Area control', rgba, out/f'area-{value}.png', True)
    assert abs(lost_area(obj, image)-expected) < .0001
image, report = fray(obj, out, 9651)
alpha = np.array(image.pixels[:]).reshape(1024, 1024, 4)[:, :, 0]
assert (alpha[:30] < .5).any()
assert (alpha[80:-80, 80:-80] == 1.).all()
assert .00001 < report['lost_area_m2'] < .0015, report
print('PASS: frayed fallen wool perimeter, intact centre and area accounting', report)
