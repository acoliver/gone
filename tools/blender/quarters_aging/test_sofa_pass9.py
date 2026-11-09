"""Blender regressions for visible sofa fringe and pressure-driven filling loss."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_decay_material import fabric_fringe

ROOT = Path(__file__).resolve().parents[3]


class Pass9Tests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_fringe_root_survives_card_minification(self):
        mat = fabric_fringe(ROOT/'tmp/age/pass9/test-fringe', 9601, (.055, .06, .066))
        texture = mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0].from_node
        image = texture.image
        alpha = np.array(image.pixels[:]).reshape(image.size[1], image.size[0], 4)[:, :, 3]
        strips = alpha.reshape(8, image.size[1]//8, image.size[0])
        # A 4 mm card occupies roughly two hero pixels. Its root needs enough
        # coverage to survive the exported 0.5 alpha cutoff after minification.
        root = strips[:, :strips.shape[1]//4]
        self.assertTrue(np.all(root.mean(axis=(1, 2)) > .55))
        self.assertTrue(np.all(strips[:, -strips.shape[1]//4:].mean(axis=(1, 2)) < .30))
        self.assertFalse(mat.use_backface_culling)
        # Force the packed payload through the same path used by glTF export.
        # Saving edited pixels must not leave the earlier packed atlas behind.
        packed_path = ROOT/'tmp/age/pass9/test-fringe/packed.png'
        packed_path.write_bytes(image.packed_file.data)
        reloaded = bpy.data.images.load(str(packed_path), check_existing=False)
        packed_alpha = np.array(reloaded.pixels[:]).reshape(reloaded.size[1], reloaded.size[0], 4)[:, :, 3]
        np.testing.assert_array_equal(alpha, packed_alpha)

    def test_clearance_field_keeps_dense_and_game_boundary_together(self):
        from fabric_mesh import material, new_object
        from sofa_pass9_finish import carry_clearance, points
        from bake_down import boundary_hausdorff
        mat = material('Control', (.3, .3, .3))
        vertices = [(0, 0, 0), (.1, 0, 0), (0, .1, 0)]
        dense = new_object('Dense', vertices, [(0, 1, 2)], mat)
        low = new_object('Game', vertices, [(0, 1, 2)], mat)
        original = points(low)
        low.data.vertices[0].co.z += .003
        self.assertGreater(boundary_hausdorff(dense, low), .003)
        report = carry_clearance(dense, low, original)
        self.assertLess(boundary_hausdorff(dense, low), .0015)
        self.assertLessEqual(report['maximum_dense_displacement_m'], .003001)

    def test_opposing_lips_curl_into_their_own_panels(self):
        from fabric_mesh import material, new_object
        from sofa_pass9_finish import open_lips
        vertices = [(-.1, 0, 0), (0, 0, 0), (0, .1, 0), (-.1, .1, 0),
                    (0, 0, 0), (.1, 0, 0), (.1, .1, 0), (0, .1, 0)]
        obj = new_object('Split', vertices, [(0, 1, 2, 3), (4, 5, 6, 7)], material('Control', (.3, .3, .3)))
        group = obj.vertex_groups.new(name='Lip shrink')
        group.add([1, 2, 4, 7], 1., 'REPLACE')
        open_lips(obj, 9601)
        self.assertLess(obj.data.vertices[1].co.x, -.001)
        self.assertGreater(obj.data.vertices[4].co.x, .001)
        self.assertAlmostEqual(obj.data.vertices[0].co.x, -.1)
        self.assertAlmostEqual(obj.data.vertices[5].co.x, .1)

    def test_back_vacuum_has_no_automatic_volume_spring(self):
        from fabric_mesh import material, new_object
        from sofa_pass8_solver import cloth
        from sofa_pass9_physics import tune
        obj = new_object('Control', [(0, 0, .2), (.02, 0, .2), (.02, .02, .2), (0, .02, .2)],
                         [(0, 1, 2, 3)], material('Control', (.3, .3, .3)))
        mod, config = cloth(obj, 4, frames=40)
        tune(obj, mod, config, 'backs')
        self.assertTrue(mod.settings.use_pressure_volume)
        self.assertEqual(mod.settings.target_volume, 0.)
        self.assertAlmostEqual(mod.settings.bending_damping, .3)
        bpy.context.scene.frame_set(40)
        self.assertAlmostEqual(mod.settings.uniform_pressure_force, -.01)
        self.assertEqual(mod.point_cache.frame_end, 2400)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Pass9Tests))
    if not result.wasSuccessful():
        raise RuntimeError('Pass-9 regressions failed')
