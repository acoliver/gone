"""Blender regressions for pass-8 opacity and bounded clearance."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fabric_mesh import material, new_object
from opacity_bake import opacity_bake
from sofa_pass8_finish import clearance
from sofa_pass8_mesh import mesh_quality

ROOT = Path(__file__).resolve().parents[3]


class Pass8Tests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_opacity_uses_texel_distance_not_zero_vertex_distances(self):
        obj = new_object('Square', [(0, 0, 0), (.1, 0, 0), (.1, .1, 0), (0, .1, 0)],
                         [(0, 1, 2, 3)], material('Cloth', (.3, .3, .3)))
        layer = obj.data.uv_layers.new(name='BakeUV')
        for loop, point in zip(layer.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop.uv = point
        image, report = opacity_bake(obj, ROOT/'tmp/age/pass8/test-opacity.png', size=128)
        pixels = np.array(image.pixels[:]).reshape(128, 128, 4)
        self.assertTrue(np.all(pixels[16:-16, 16:-16, 0] == 1))
        self.assertGreater(report['transparent_texels'], 0)
        self.assertIn('per-texel', report['distance_method'])

    def test_clearance_preserves_rigid_and_bounds_displacement(self):
        mat = material('Control', (.3, .3, .3))
        rigid = new_object('Rigid', [(-1, -1, 0), (1, -1, 0), (0, 1, 0)], [(0, 1, 2)], mat)
        cloth = new_object('Cloth', [(-.1, 0, -.0005), (.1, 0, .0005), (0, .1, .0005)], [(0, 1, 2)], mat)
        original = np.array([v.co[:] for v in cloth.data.vertices])
        fixed = np.array([v.co[:] for v in rigid.data.vertices])
        report = clearance([cloth, rigid], {'Cloth'})
        self.assertGreater(report['counts'][0], 0, report)
        self.assertTrue(report['pass'], report)
        np.testing.assert_array_equal(fixed, [v.co[:] for v in rigid.data.vertices])
        self.assertLessEqual(np.linalg.norm(np.array([v.co[:] for v in cloth.data.vertices])-original, axis=1).max(), .003001)

    def test_wall_and_top_weights_have_different_bending_limits(self):
        from sofa_pass8_solver import cloth
        obj = new_object('Weighted cloth', [(0, 0, .2), (.02, 0, .2), (.02, .02, .2), (0, .02, .2)],
                         [(0, 1, 2, 3)], material('Control', (.3, .3, .3)))
        group = obj.vertex_groups.new(name='Welt')
        group.add([0, 1], .1, 'REPLACE')
        group.add([2, 3], 1., 'REPLACE')
        mod, config = cloth(obj, 4, frames=2)
        self.assertEqual(mod.settings.bending_stiffness, 0.)
        self.assertAlmostEqual(mod.settings.bending_stiffness_max, config['bending'], places=5)
        self.assertEqual(mod.settings.vertex_group_bending, 'Welt')
        self.assertEqual(mod.settings.tension_damping, 5.)
        self.assertAlmostEqual(mod.settings.bending_damping, .3)

    def test_quality_rejects_sliver_without_excluding_it(self):
        obj = new_object('Sliver', [(0, 0, 0), (.1, 0, 0), (.05, .00001, 0)],
                         [(0, 1, 2)], material('Control', (.3, .3, .3)))
        result = mesh_quality(obj)
        self.assertFalse(result['pass'])
        self.assertFalse(result['self_collision_exclusions'])

    def test_back_ties_pin_existing_vertices_without_creating_slivers(self):
        from sofa_pass8_mesh import tie_pins
        xs = [-.21, -.19, -.01, .01, .19, .21]
        vertices = [(x, .37, z) for z in [.59, .61, .63] for x in xs]
        faces = [(i, i+1, i+7, i+6) for row in range(2) for i in range(row*6, row*6+5)]
        obj = new_object('Back', vertices, faces, material('Cloth', (.3, .3, .3)))
        original = np.array([v.co[:] for v in obj.data.vertices])
        pins, patches = tie_pins(obj)
        self.assertEqual(len(patches), 3)
        self.assertTrue(pins)
        np.testing.assert_array_equal(original, [v.co[:] for v in obj.data.vertices])
        self.assertTrue(all(.60 <= original[i, 2] <= .62 for i in pins))
        self.assertTrue(mesh_quality(obj)['pass'])

    def test_right_back_residue_starts_inside_the_lower_return(self):
        from sofa_full_decay import initialize
        from sofa_pass8 import prepare
        from sofa_pass8_finish import initial_contacts
        initialize()
        obj, detail, driver, _ = prepare('BackCushion_R', ROOT/'tmp/age/pass8')
        result = initial_contacts(obj, [bpy.data.objects['BackCushion_R_Residue']])
        self.assertTrue(result['pass'])
        self.assertTrue(detail['mesh_quality']['pass'])
        self.assertIsNone(driver)
        self.assertNotIn('BackCushion_R_Envelope', bpy.data.objects)

    def test_fitted_throw_has_one_bridge_and_a_pinned_cap(self):
        from sofa_full_decay import initialize
        from sofa_pass8 import prepare_throw
        initialize()
        obj = bpy.data.objects['Throw']
        _, _, splits, pins = prepare_throw(obj)
        self.assertGreaterEqual(splits['split_share'], .88)
        self.assertLessEqual(splits['split_share'], .90)
        self.assertGreaterEqual(splits['rear_bridge_length_m'], .055)
        self.assertLessEqual(splits['rear_bridge_length_m'], .070)
        self.assertTrue(pins)
        self.assertTrue(mesh_quality(obj)['pass'])
        self.assertLess(splits['runs'][0]['split_bounds_local_m'][0][1], -.46)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Pass8Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError('Pass-8 regressions failed')
