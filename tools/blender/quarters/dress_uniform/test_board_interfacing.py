"""A stiffened board must not inherit independent triangle rotations as folds."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source, reinforce_and_bind
from detail_clearance import fit_boards, seat_details
from reduced_clearance import crossing_pairs
from common import recalc

body = load_source()
bindings, _ = reinforce_and_bind(body)
for vertex in body.data.vertices:
    vertex.co.y += .006*np.sin(vertex.co.x*40)
recalc(body)
fit_boards(body, bindings)
selected = {name: bindings[name] for name in ('ShoulderBoard_L', 'ShoulderBoard_R')}
seat_details(body, selected)
for name, binding in selected.items():
    obj = bpy.data.objects[name]
    points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    original = np.asarray(binding['original'])
    np.testing.assert_allclose(np.linalg.norm(points[:, None]-points[None, :], axis=2),
                               np.linalg.norm(original[:, None]-original[None, :], axis=2), atol=1e-7)
    assert not crossing_pairs(obj), name
    assert not crossing_pairs(obj, body), name
print('PASS: original board curvature survives changed wool with zero self and support crossings')
