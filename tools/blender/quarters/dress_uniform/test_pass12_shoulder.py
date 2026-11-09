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
from mathutils.bvhtree import BVHTree
board = bpy.data.objects['ShoulderBoard_L']
tree = BVHTree.FromObject(board, bpy.context.evaluated_depsgraph_get())
distance = np.array([tree.find_nearest(board.matrix_world.inverted() @ (body.matrix_world @ v.co))[3]
                     for v in body.data.vertices])
open_shoulder(body)
after = np.array([v.co[:] for v in body.data.vertices])
front = pattern[:, 0] < .48
np.testing.assert_array_equal(before[front & (before[:, 0] <= .18)], after[front & (before[:, 0] <= .18)])
np.testing.assert_array_equal(before[front & (distance <= .008)], after[front & (distance <= .008)])
np.testing.assert_array_equal(before[front & (pattern[:, 1] <= .90)], after[front & (pattern[:, 1] <= .90)])
free_front = front & (pattern[:, 1] > .93) & (before[:, 0] > .18) & (before[:, 0] < .235)
free_front &= distance > .014
assert free_front.any()
assert np.median((after-before)[free_front, 1]) < -.005, 'The free front lip must emerge in front of the board'
assert np.median((after-before)[free_front, 2]) > .020, 'The free front lip must clear the occluding shoulder silhouette'
rear = (pattern[:, 0] > .48) & (pattern[:, 0] < 1) & (pattern[:, 1] > .93)
rear &= (before[:, 0] > .18) & (before[:, 0] < .235) & (before[:, 1] > .008)
assert rear.any()
assert np.median((after-before)[rear, 1]) > .003
print('PASS: both free shoulder lips open while actual front fitting-support cloth stays fixed')
