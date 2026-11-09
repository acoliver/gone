"""Sewn board columns retain their thickness and clear continuous wool faces."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source, reinforce_and_bind
from detail_clearance import fit_boards, seat_board_columns, seat_details
from reduced_clearance import crossing_pairs, push_out

body = load_source()
bindings, _ = reinforce_and_bind(body)
fit_boards(body, bindings)
selected = {name: bindings[name] for name in ('ShoulderBoard_L', 'ShoulderBoard_R')}
seat_details(body, selected)
before = {name: np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
          for name in selected for obj in [bpy.data.objects[name]]}
seat_board_columns(body, selected)
for name, points in before.items():
    obj = bpy.data.objects[name]
    count = len(points)//2
    seated = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    np.testing.assert_allclose(seated[count:]-seated[:count], points[count:]-points[:count], atol=1e-7)
    assert not crossing_pairs(obj), name
    report = push_out(obj, body, paired=True)
    assert report['crossings_after'] == 0, (name, report)
    assert not crossing_pairs(obj), name
print('PASS: board facings retain paired thickness and have zero support and self crossings')
