"""Blender regressions for pass-10 cover fairing and residue material bakes."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fabric_mesh import material, new_object
from sofa_pass10_mesh import fair_interior, restore_hold_patch
from sofa_pass10_material import foam_albedo


class Pass10Tests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def grid(self):
        vertices = [(x*.02, y*.02, .009 if x == y == 2 else 0.)
                    for y in range(5) for x in range(5)]
        faces = [(y*5+x, y*5+x+1, (y+1)*5+x+1, (y+1)*5+x)
                 for y in range(4) for x in range(4)]
        return new_object('Cover', vertices, faces, material('Control', (.2, .2, .2)))

    def test_fairing_preserves_boundary_and_bounds_displacement(self):
        obj = self.grid()
        original = np.array([v.co[:] for v in obj.data.vertices])
        report = fair_interior(obj, maximum=.003, iterations=10)
        result = np.array([v.co[:] for v in obj.data.vertices])
        boundary = [y*5+x for y in range(5) for x in range(5)
                    if x in (0, 4) or y in (0, 4)]
        np.testing.assert_array_equal(result[boundary], original[boundary])
        self.assertLess(result[12, 2], original[12, 2])
        self.assertLessEqual(np.linalg.norm(result-original, axis=1).max(), .003001)
        self.assertLessEqual(report['maximum_displacement_m'], .003001)

    def test_fairing_keeps_retained_stitches(self):
        obj = self.grid()
        obj.vertex_groups.new(name='Retained stitches').add([12], 1., 'REPLACE')
        original = obj.data.vertices[12].co.copy()
        fair_interior(obj, maximum=.006)
        self.assertEqual(obj.data.vertices[12].co, original)

    def test_hold_restoration_is_local_and_does_not_move_stitches(self):
        obj = self.grid()
        rest = np.array([v.co[:] for v in obj.data.vertices])
        obj.vertex_groups.new(name='Retained stitches').add([12], 1., 'REPLACE')
        obj.data.vertices[13].co.z = .015
        before = np.array([v.co[:] for v in obj.data.vertices])
        restore_hold_patch(obj, rest, centre=(.04, .04, 0.), inner=.025, outer=.035)
        self.assertEqual(obj.data.vertices[12].co.z, before[12, 2])
        self.assertAlmostEqual(obj.data.vertices[13].co.z, 0.)
        np.testing.assert_array_equal(np.array([v.co[:] for v in obj.data.vertices])[[0, 4, 20, 24]], before[[0, 4, 20, 24]])

    def test_torn_coverage_is_monotone_inward_without_a_straight_cap(self):
        from sofa_pass10_opacity import torn_coverage
        y = np.linspace(0, .1, 500)
        roots = np.c_[np.zeros(len(y)), y, np.zeros(len(y))]
        near = torn_coverage(roots, np.full(len(y), .001), roots, 9601)
        capped = torn_coverage(roots, np.full(len(y), .003), roots, 9601)
        far = torn_coverage(roots, np.full(len(y), .010), roots, 9601)
        self.assertTrue(np.all(~near | capped))
        self.assertTrue(np.all(~capped | far))
        self.assertTrue(far.all())
        self.assertTrue(capped.any())
        self.assertFalse(capped.all())

    def test_stress_opening_cuts_both_close_parallel_plies(self):
        from sofa_pass10_opacity import torn_coverage
        points = np.array([[0., 0., 0.], [0., 0., .025], [.1, 0., 0.]])
        opening = {'centre': np.zeros(3), 'tangent': np.array([1, 0, 0]),
                   'across': np.array([0, 1, 0])}
        result = torn_coverage(points, np.ones(3), points, 9601, opening)
        np.testing.assert_array_equal(result, [False, False, True])

    def test_rasterized_stress_opening_reaches_its_authored_uv(self):
        from unittest.mock import patch
        from sofa_pass10_opacity import opacity
        obj = new_object('Cover', [(-.1, -.1, 0), (.1, -.1, 0), (.1, .1, 0), (-.1, .1, 0)],
                         [(0, 1, 2, 3)], material('Control', (.2, .2, .2)))
        uv = obj.data.uv_layers.new(name='BakeUV')
        for loop, point in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop.uv = point
        opening = {'centre': np.zeros(3), 'tangent': np.array([1, 0, 0]),
                   'across': np.array([0, 1, 0])}
        out = Path(__file__).resolve().parents[3]/'tmp/age/pass10/test-opacity/raster.png'
        with patch('sofa_pass10_opacity.opening_for', return_value=opening), np.errstate(all='raise'):
            image, _ = opacity(obj, out, 9601, size=256)
        pixels = np.array(image.pixels[:]).reshape(256, 256, 4)
        self.assertEqual(pixels[128, 128, 0], 0.)
        self.assertEqual(pixels[64, 64, 0], 1.)
        self.assertTrue(np.isfinite(pixels).all())

    def test_nonshrinking_fairing_retains_more_of_a_broad_fold(self):
        obj = self.grid()
        other = self.grid()
        fair_interior(obj, maximum=.006, iterations=5)
        fair_interior(other, maximum=.006, iterations=5, nonshrinking=True)
        self.assertGreater(other.data.vertices[12].co.z, obj.data.vertices[12].co.z)

    def test_residue_detail_matches_at_shared_dense_and_game_points(self):
        from sofa_pass10_mesh import roughen_residue
        obj, other = self.grid(), self.grid()
        original = np.array([v.co[:] for v in obj.data.vertices])
        roughen_residue(obj, 9601)
        roughen_residue(other, 9601)
        result = np.array([v.co[:] for v in obj.data.vertices])
        np.testing.assert_array_equal(result, np.array([v.co[:] for v in other.data.vertices]))
        self.assertTrue((np.abs(result-original).max(axis=0) > 0).all())
        self.assertLessEqual(np.linalg.norm(result-original, axis=1).max(), .0015*np.sqrt(3)+1e-7)

    def test_powder_grains_have_open_space_and_repeat_for_the_same_seed(self):
        from sofa_pass10_debris import grain_pixels
        first = grain_pixels(9710, size=128)
        np.testing.assert_array_equal(first, grain_pixels(9710, size=128))
        self.assertGreater(first[:, :, 3].mean(), .05)
        self.assertLess(first[:, :, 3].mean(), .4)
        self.assertTrue((first[:, :, 0] > first[:, :, 2]).all())

    def test_foam_albedo_keeps_shadow_detail_without_black_insert(self):
        ao = np.ones((3, 3, 4), dtype=np.float32)
        ao[:, :, :3] = np.linspace(0, 1, 9).reshape(3, 3, 1)
        albedo = foam_albedo(ao)
        self.assertTrue(np.isfinite(albedo).all())
        self.assertTrue((albedo[:, :, :3] > 0).all())
        self.assertTrue(np.all(np.diff(albedo[:, :, 0].ravel()) > 0))
        self.assertGreater(albedo[-1, -1, 0], albedo[-1, -1, 2])
        np.testing.assert_array_equal(albedo[:, :, 3], 1.)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Pass10Tests))
    if not result.wasSuccessful():
        raise RuntimeError('Pass-10 regressions failed')
