"""Seat the rejected board bases without trading gaps for triangle crossings."""
from pathlib import Path
import json
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from board_seating import seat_boards
from detail_clearance import seat_details

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/tunic8/final/baked.blend'))
record = json.loads(bpy.context.scene['tunic5_record'])
before = {name: np.array([v.co[:] for v in bpy.data.objects[name].data.vertices])
          for name in ['ShoulderBoard_L', 'ShoulderBoard_R']}
report = seat_boards(bpy.data.objects['TunicBody'], record['bindings'])
for name, item in report.items():
    assert item['within_2mm'], (name, item)
    assert item['self_crossings'] == item['body_crossings'] == 0, (name, item)
    obj = bpy.data.objects[name]
    points = np.array([v.co[:] for v in obj.data.vertices])
    count = len(points)//2
    assert item['maximum_column_offset_change_m'] < 1e-7, item
    assert len(points) > len(before[name]), 'Shoulder creases need resolved facing grids'
    seat_details(bpy.data.objects['TunicBody'], {name: record['bindings'][name]})
    np.testing.assert_array_equal(points, np.array([v.co[:] for v in obj.data.vertices]))
print(json.dumps(report, indent=2))
print('PASS: both board bases within 2 mm; unchanged column thickness; zero self/body SAT; no finishing re-lift')
