import unittest
import numpy as np
from visibility_gates import dust_visibility, longest_straight_boundary, secondary_correlation, strip_metrics
from locker_gates import rust_pixels


class VisibilityTests(unittest.TestCase):
    def test_invisible_dust_fails_even_at_full_coverage(self):
        image = np.full((30, 30, 3), .4)
        up = np.ones((30, 30), bool)
        self.assertLess(dust_visibility(image + .01, image, up), .06)
        self.assertGreater(dust_visibility(image + .2, image, up), .06)

    def test_straight_rectangle_boundary_fails(self):
        rust = np.zeros((120, 120), bool)
        rust[20:100, 20:100] = True
        self.assertGreater(longest_straight_boundary(rust, np.ones_like(rust), 1000), .04)

    def test_periodic_albedo_fails(self):
        yy, xx = np.indices((256, 256))
        image = np.repeat((.4 + .2 * np.sin(xx / 64 * 2 * np.pi))[..., None], 3, -1)
        self.assertGreater(secondary_correlation(image, 500), .5)

    def test_random_albedo_passes(self):
        image = np.random.default_rng(95).random((256, 256, 3))
        self.assertLess(secondary_correlation(image, 500), .5)

    def test_wide_rust_smear_fails(self):
        image = np.full((200, 100, 3), .6)
        image[:, 25:75] = [.4, .14, .04]
        value = strip_metrics(image, np.ones((200, 100), bool), 50, np.ones(200, bool), 1000, rust_pixels)
        self.assertGreater(value['width_m'], .015)
        self.assertFalse(value['passed'])


if __name__ == '__main__':
    unittest.main()
