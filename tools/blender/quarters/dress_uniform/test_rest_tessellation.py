"""The evaluated garment must not need sub-contact rest-face exclusions."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source
from aging_geometry import refine, cut_tunic, detach_fallen, pressed_sleeve
from rest_carrier import prepare_carrier, add_rest_carrier

body = load_source()
refine(body)
cut_tunic(body)
detach_fallen(body)
prepare_carrier(body)
pressed_sleeve(body)
add_rest_carrier(body)
evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
evaluated.data.calc_loop_triangles()
v = np.array([p.co[:] for p in evaluated.data.vertices])
f = np.array([t.vertices[:] for t in evaluated.data.loop_triangles])
t = v[f]
longest = np.linalg.norm(t-np.roll(t, 1, axis=1), axis=2).max(1)
altitude = np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1)/longest
assert altitude.min() >= .002, (float(altitude.min()), int((altitude < .002).sum()))
assert body.vertex_groups.get('Self collision exclusion') is None
print('PASS: no evaluated rest triangle has altitude below 2 mm', altitude.min(), len(f))
