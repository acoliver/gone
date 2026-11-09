"""A stiff rear lip is free cloth, not the shoulder board's front support ply."""
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from polish_pass9 import vertex_pattern
from polish_pass12 import open_shoulder

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/tunic11/visible/baked.blend'))
body = bpy.data.objects['TunicBody']
pattern = vertex_pattern(body)
before = np.array([v.co[:] for v in body.data.vertices])
open_shoulder(body)
after = np.array([v.co[:] for v in body.data.vertices])
np.testing.assert_array_equal(before[pattern[:, 0] < .48], after[pattern[:, 0] < .48])
rear = (pattern[:, 0] > .48) & (pattern[:, 0] < 1) & (pattern[:, 1] > .93)
rear &= (before[:, 0] > .18) & (before[:, 0] < .235) & (before[:, 1] > .008)
assert rear.any()
assert np.median((after-before)[rear, 1]) > .003
print('PASS: rear shoulder lip opens while the front fitting-support ply is unchanged')
