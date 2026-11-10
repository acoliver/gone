"""Sewn fabric facings must follow the final support, not a whole-object plane."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source, reinforce_and_bind, fit_details
from common import recalc, surface_tree
from detail_clearance import seat_sewn

body = load_source()
bindings, _ = reinforce_and_bind(body)
for vertex in body.data.vertices:
    vertex.co.y += .005*np.sin(vertex.co.x*24)
recalc(body)
fit_details(body, bindings)
seat_sewn(body, bindings)
tree = surface_tree(body)
for name in ('ShoulderBoard_L', 'ShoulderBoard_R', 'Placket'):
    obj = bpy.data.objects[name]
    gaps = [tree.find_nearest(obj.matrix_world @ v.co)[3] for v in obj.data.vertices]
    assert min(gaps) > 0, (name, min(gaps))
    assert max(gaps) <= .002, (name, max(gaps))
print('PASS: sewn board and placket vertices remain within 2 mm of changed support')
