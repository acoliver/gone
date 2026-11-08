"""Run in Blender: group semantics must match Blender's exclusion API."""
import sys
import unittest
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth_stage import calibrated_config, configure


class ClothGroups(unittest.TestCase):
    def test_calibration_formula_reproduces_the_mass_conserving_fit(self):
        upholstery = calibrated_config('upholstery', .2/34, .2/9, 150)
        self.assertAlmostEqual(upholstery['mass'], .015)
        self.assertAlmostEqual(upholstery['stiffness'], 160.)
        self.assertAlmostEqual(upholstery['shear'], 56.)
        self.assertAlmostEqual(upholstery['bending'], 1.6)
        self.assertAlmostEqual(upholstery['damping_factor'], .12)
        wool = calibrated_config('wool', .2/34, .2/9, 150)
        self.assertAlmostEqual(wool['mass'], .15)
        self.assertAlmostEqual(wool['bending'], .25)
        self.assertAlmostEqual(wool['stiffness'], 150.)

    def test_only_lip_group_shrinks_and_self_group_is_an_exclusion(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_plane_add()
        obj = bpy.context.object
        obj.vertex_groups.new(name='Lip shrink')
        obj.vertex_groups.new(name='Self collision exclusion')
        mod = configure(obj, {'mass': .015, 'stiffness': 180, 'bending': .2,
                              'frames': 20, 'self_collision': True, 'shrink': .04}, 4)
        self.assertEqual(mod.settings.shrink_min, 0.)
        self.assertAlmostEqual(mod.settings.shrink_max, .04)
        self.assertEqual(mod.collision_settings.vertex_group_self_collisions, 'Self collision exclusion')
        self.assertIn('not used', bpy.types.ClothCollisionSettings.bl_rna.properties[
            'vertex_group_self_collisions'].description)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
