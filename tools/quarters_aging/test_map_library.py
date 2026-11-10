"""Regression controls for classification, variation and existing-UV rasterization."""
import unittest

import numpy as np

from map_library import classify_face, choose_face, triangle_samples, projection_frame


class LibraryMappingTests(unittest.TestCase):
    def test_upward_face_is_top_even_when_narrow(self):
        self.assertEqual(classify_face([0, 0, 1], [.04, 1], .04), 'top')
        self.assertEqual(classify_face([0, 0, -1], [.5, 1], .5), 'broad')

    def test_area_and_aspect_select_strip(self):
        self.assertEqual(classify_face([0, -1, 0], [.04, 1], .04), 'strip')
        self.assertEqual(classify_face([0, -1, 0], [.05, .05], .0025), 'strip')
        self.assertEqual(classify_face([0, -1, 0], [.5, 1], .5), 'broad')

    def test_seeded_choice_avoids_neighbor_and_prefers_aspect(self):
        rows = [dict(id='a', kind='broad', pixels=[400, 800]),
                dict(id='b', kind='broad', pixels=[400, 800]),
                dict(id='c', kind='broad', pixels=[800, 400])]
        a = choose_face(rows, 'broad', [.5, 1], 95, 'Door', set())
        self.assertEqual(a, choose_face(rows, 'broad', [.5, 1], 95, 'Door', set()))
        b = choose_face(rows, 'broad', [.5, 1], 95, 'NextDoor', {a['id']})
        self.assertNotEqual(a['id'], b['id'])
        self.assertNotEqual(b['id'], 'c')

    def test_absent_class_fails(self):
        with self.assertRaises(ValueError):
            choose_face([], 'top', [1, 1], 1, 'test', set())

    def test_uv_triangle_pixel_centres_and_barycentric_interpolation(self):
        uv = np.array([[0, 0], [1, 0], [0, 1]])
        x, y, weights = triangle_samples(uv, 8)
        self.assertTrue(len(x) > 0)
        reconstructed = weights @ uv
        np.testing.assert_allclose(reconstructed[:, 0], (x+.5)/8)
        np.testing.assert_allclose(reconstructed[:, 1], 1-(y+.5)/8)
        np.testing.assert_allclose(weights.sum(1), 1)
        self.assertTrue((weights >= -1e-8).all())

    def test_degenerate_uv_fails(self):
        with self.assertRaises(ValueError):
            triangle_samples(np.zeros((3, 2)), 8)

    def test_projection_uses_world_up_on_vertical_panel(self):
        points = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 2], [0, 0, 2]])
        projected, size = projection_frame(points, [0, -1, 0])
        np.testing.assert_allclose(size, [1, 2])
        np.testing.assert_allclose(projected[:, 1], [0, 0, 1, 1])


if __name__ == '__main__':
    unittest.main()
