"""Background Blender control for structural and bending sleeve rest shapes."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_geometry import cut_tunic, detach_fallen, pressed_sleeve, refine
from aging_support import load_source
from common import recalc

body = load_source()
refine(body)
cut_tunic(body)
detach_fallen(body)
uv = body.data.uv_layers[0].data
sleeve = sorted({loop.vertex_index for loop in body.data.loops
                 if 1.099 < uv[loop.index].uv.x < 1.551})
original = np.array([v.co[:] for v in body.data.vertices])
rest = pressed_sleeve(body)
recalc(body)
actual = np.array([v.co[:] for v in body.data.vertices])
bending = np.array([v.co[:] for v in rest.data])
ids = np.array([i for i in sleeve if -.70 < original[i, 2] < -.60])
assert np.max(np.abs(actual[ids, 1]-bending[ids, 1])) < 1e-7, 'Structural sleeve over-compressed relative to its 40% bending rest'
assert len(ids) > 10
progress = np.clip((-.425-original[ids, 2])/.44, 0, 1)
center = np.c_[.326+.013*progress, -.008-.027*progress]
angle = np.arctan2(.3, .9)
rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
expected = (original[ids, :2]-center)*[1.2, .4]
np.testing.assert_allclose((actual[ids, :2]-center)@rotation, expected, atol=1e-7)
np.testing.assert_allclose((bending[ids, :2]-center)@rotation, expected, atol=1e-7)
assert np.isfinite(actual).all() and np.isfinite(bending).all()
print('PASS: structural and bending rest agree in the camera-facing pressed frame', flush=True)
