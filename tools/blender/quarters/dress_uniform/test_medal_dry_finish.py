"""Fine-finish filtering preserves the geometric bake and removes subpixel noise."""
import unittest

import numpy as np

from medal_dry_finish import filtered_detail_normal


class FilteredDetailNormalTests(unittest.TestCase):
    def test_geometry_is_preserved_without_fine_detail(self):
        y, x = np.mgrid[:32, :32]
        geometry = np.stack((x / 320, y / 320, np.ones_like(x)), -1)
        geometry /= np.linalg.norm(geometry, axis=2, keepdims=True)
        np.testing.assert_allclose(filtered_detail_normal(geometry, geometry), geometry, atol=1e-12)

    def test_checker_detail_is_filtered_without_flattening_geometry(self):
        y, x = np.mgrid[:64, :64]
        geometry = np.stack((x / 320, np.zeros_like(x), np.ones_like(x)), -1)
        geometry /= np.linalg.norm(geometry, axis=2, keepdims=True)
        normal = geometry.copy()
        normal[:, :, 1] += np.where((x + y) % 2, .02, -.02)
        normal /= np.linalg.norm(normal, axis=2, keepdims=True)
        filtered = filtered_detail_normal(normal, geometry)
        self.assertLess(np.std(filtered[:, :, 1]), np.std(normal[:, :, 1]) * .01)
        self.assertGreater(np.ptp(filtered[:, :, 0]), .18)
        np.testing.assert_allclose(np.linalg.norm(filtered, axis=2), 1, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
