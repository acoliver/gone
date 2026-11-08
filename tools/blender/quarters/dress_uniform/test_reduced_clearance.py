"""A reduced triangle crossing its support must be pushed clear, not excluded."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fabric_mesh import material, new_object
from reduced_clearance import crossing_pairs, push_out

bpy.ops.wm.read_factory_settings(use_empty=True)
mat = material('Control', (.1, .1, .1))
support = new_object('Support', [(-.1, -.1, 0), (.1, -.1, 0), (0, .1, 0)], [(0, 1, 2)], mat)
cloth = new_object('Cloth', [(-.01, 0, -.0004), (.01, 0, .0002), (0, .01, .0002)], [(0, 1, 2)], mat)
assert crossing_pairs(cloth, support)
report = push_out(cloth, support)
assert report['crossings_after'] == 0, report
assert report['maximum_motion_m'] <= .003
assert min(v.co.z for v in cloth.data.vertices) >= .0004999
assert len(cloth.data.vertices) == 3 and len(cloth.data.polygons) == 1
print('PASS: strict SAT is zero after bounded push-out; no topology changes or exemptions', report)
