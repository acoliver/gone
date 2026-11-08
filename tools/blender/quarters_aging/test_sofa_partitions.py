"""Blender controls for fitted seam barriers and retained rest-key carriers."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import assert_collision_clear
from sofa_decay_policy import ORDER
from sofa_full_decay import initialize, open_cover_bottom
from foam_collapse import largest_shell
from sofa_partitions import clear_partitions, fitted_back_barriers, fitted_bounds, install_partitions, partition_plan


class Partitions(unittest.TestCase):
    def setUp(self):
        initialize()
        self.points = fitted_bounds()

    def test_side_seams_are_between_fitted_footprints(self):
        plan = partition_plan(self.points)
        seams = [centre[0] for name, centre, _ in plan if name.startswith('seam_')]
        self.assertAlmostEqual(seams[0], -.33506623, places=6)
        self.assertAlmostEqual(seams[1], .33493379, places=6)

    def test_each_fitted_cover_starts_clear_and_slabs_never_export(self):
        for name in ORDER:
            back = name.startswith('Back')
            install_partitions(self.points, back)
            if not back:
                fitted_back_barriers()
            obj = bpy.data.objects[name]
            largest_shell(obj)
            open_cover_bottom(obj, back)
            assert_collision_clear(obj)
            slabs = [o for o in bpy.context.scene.objects if o.name.startswith('CushionPartition_')]
            self.assertTrue(slabs)
            self.assertTrue(all(not o['aged_export'] and o.hide_render for o in slabs))
        clear_partitions()
        self.assertFalse(any(o.name.startswith('CushionPartition_') for o in bpy.context.scene.objects))


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
