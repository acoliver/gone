"""Small positive and negative controls for the continuous collision predicate."""
import unittest

import numpy as np

from triangle_contacts import intersect


class TriangleContacts(unittest.TestCase):
    def setUp(self):
        self.a = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])

    def test_crossing_without_inside_vertices(self):
        b = [[.2, -.2, -1], [.2, -.2, 1], [.2, 1.2, 0]]
        self.assertTrue(intersect(self.a, b))

    def test_coplanar_overlap(self):
        self.assertTrue(intersect(self.a, self.a + [.1, .1, 0]))

    def test_coplanar_disjoint_with_overlapping_aabbs(self):
        b = [[.8, .8, 0], [1.8, .8, 0], [.8, 1.8, 0]]
        self.assertFalse(intersect(self.a, b))

    def test_parallel_separated(self):
        self.assertFalse(intersect(self.a, self.a + [0, 0, .001]))

    def test_symmetry(self):
        b = self.a + [.1, .1, 0]
        self.assertEqual(intersect(self.a, b), intersect(b, self.a))


class HemNotches(unittest.TestCase):
    def test_even_notches_fail_variation_gate(self):
        from visible_gates import notch_depths
        depths = notch_depths(np.tile([0., .010, 0.], 12))
        self.assertLess(depths.std() / depths.mean(), .40)

    def test_varying_notches_pass_variation_gate(self):
        from visible_gates import notch_depths
        depths = notch_depths(np.tile([0., .002, 0., .014, 0., .003, 0., .022], 4))
        self.assertGreater(depths.std() / depths.mean(), .40)


class ProjectedCoverage(unittest.TestCase):
    def test_front_geometry_occludes_target(self):
        import trimesh
        from visible_gates import projected_masks
        points = [[-1., -1., 0.], [1., -1., 0.], [1., 1., 0.], [-1., 1., 0.]]
        target = trimesh.Trimesh(points, [[0, 1, 2], [0, 2, 3]], process=False)
        occluder = target.copy()
        occluder.vertices[:, 2] = 1.
        visible, hidden = projected_masks([target], [target], np.array([0., 0., 3.]), [0., 0., 0.], size=80, occluders=([], [occluder]))
        self.assertTrue(visible.any())
        self.assertFalse(hidden.any())
        occluder.vertices[:, 2] = -1.
        _, unobstructed = projected_masks([target], [target], np.array([0., 0., 3.]), [0., 0., 0.], size=80, occluders=([], [occluder]))
        np.testing.assert_array_equal(visible, unobstructed)


if __name__ == '__main__':
    unittest.main()
