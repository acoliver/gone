import unittest

import numpy as np
from scipy.spatial.distance import pdist, squareform

from locker_blisters import angular_wave, corrugate, shape_profiles, spots


class LockerBlisterTests(unittest.TestCase):
    def test_irregular_profiles_preserve_area_and_remain_under_sixty_mm(self):
        radii = np.array([.006, .012, .021, .024])
        amplitude, phase, bias, limit = shape_profiles(radii, .006, 9501)
        angles = np.linspace(0, 2 * np.pi, 256, endpoint=False)
        wave = angular_wave(angles[None], amplitude[:, None], phase[:, None])
        profile = np.clip(radii[:, None] * (bias[:, None] + wave), radii[:, None] * .10, limit[:, None])
        np.testing.assert_allclose((profile ** 2).mean(-1), radii ** 2, rtol=1e-5)
        self.assertGreater(float(np.ptp(profile[0])), .003)
        self.assertLess(float(limit.max() * 2 + .006 + .004 + .0015), .060)

    def test_corrugation_preserves_area_and_bounds_the_physical_displacement(self):
        uv = np.column_stack([np.linspace(0, .6, 1000), np.linspace(0, 2.4, 1000)])
        warped = corrugate(uv, 9501)
        np.testing.assert_array_equal(warped[:, 1], uv[:, 1])
        self.assertLessEqual(float(abs(warped[:, 0] - uv[:, 0]).max()), .003)
        shifted = corrugate(uv + [.01, 0], 9501)
        np.testing.assert_allclose(shifted - warped, np.tile([.01, 0], (len(uv), 1)), atol=1e-8)
        self.assertGreater(float(np.std(np.diff(warped[:, 0] - uv[:, 0]))), 1e-5)

    def test_islands_stay_under_sixty_mm_with_paint_between_them(self):
        centres, radii = spots([[0, 0], [.6, 2.4]], .37, (.015, .023), 9501)
        self.assertLess(float(radii.max() * 2 + .006 + .004 + .0015), .060)
        distances = squareform(pdist(centres))
        gap = distances - radii[:, None] - radii[None, :]
        np.fill_diagonal(gap, np.inf)
        self.assertGreaterEqual(float(gap.min()), .008)

    def test_side_blisters_reach_coverage_without_touching(self):
        centres, radii = spots([[0, 0], [.62, 2.46]], .42, (.021, .024), 9501, gap=.006)
        distances = squareform(pdist(centres))
        separation = distances - radii[:, None] - radii[None, :]
        np.fill_diagonal(separation, np.inf)
        self.assertGreaterEqual(float(separation.min()), .006)
        self.assertLess(float(radii.max() * 2 + .006 + .004 + .0015), .060)
        self.assertGreaterEqual(float((np.pi * radii ** 2).sum() / (.62 * 2.46)), .42)

    def test_side_coverage_can_mix_small_and_large_islands(self):
        _, radii = spots([[0, 0], [.62, 2.46]], .42, (.006, .024), 9501, gap=.006)
        self.assertLess(float(np.quantile(radii, .25)), .010)
        self.assertGreater(float(np.quantile(radii, .95)), .020)
        self.assertGreaterEqual(float((np.pi * radii ** 2).sum() / (.62 * 2.46)), .42)

    def test_spot_area_reaches_the_requested_coverage(self):
        _, radii = spots([[0, 0], [.6, 2.4]], .16, (.007, .021), 9501)
        self.assertGreaterEqual(float((np.pi * radii ** 2).sum() / (0.6 * 2.4)), .16)

    def test_spots_are_seeded_without_a_repeated_grid(self):
        a = spots([[0, 0], [.6, 2.4]], .16, (.007, .021), 9501)
        b = spots([[0, 0], [.6, 2.4]], .16, (.007, .021), 9501)
        for left, right in zip(a, b):
            np.testing.assert_array_equal(left, right)
        self.assertGreater(float(np.std(np.diff(np.sort(a[0][:, 0])))), .001)


if __name__ == '__main__':
    unittest.main()
