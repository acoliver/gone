"""Blender controls for physical grain direction and finite walk termination."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grain_paths import surface_walk


class GrainWalk(unittest.TestCase):
    def test_rotated_pattern_preserves_requested_start_direction_and_length(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new('Pattern')
        mesh.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2), (0, 2, 3)])
        obj = bpy.data.objects.new('Pattern', mesh)
        bpy.context.collection.objects.link(obj)
        layer = mesh.uv_layers.new(name='Rotated grain')
        for loop in mesh.loops:
            p = mesh.vertices[loop.vertex_index].co
            layer.data[loop.index].uv = (p.y, -p.x)
        points = np.array(surface_walk(obj, (0, 0, 0), .18, 9501, direction=(1, 0, 0)))
        self.assertGreater(points[1, 0], points[0, 0])
        length = np.linalg.norm(np.diff(points, axis=0), axis=1).sum()
        self.assertAlmostEqual(length, .18, places=6)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
