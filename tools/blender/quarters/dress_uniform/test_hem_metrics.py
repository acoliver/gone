"""Periodicity must mean a repeated hem, rather than a broad garment slope."""
import unittest
import numpy as np

from hem_metrics import periodic_peak


class HemMetricsTests(unittest.TestCase):
    def test_regular_notches_fail_at_inclusive_lag_limits(self):
        x = np.arange(600)*.001
        for period in [.020, .040, .120]:
            with self.subTest(period=period):
                peak, _ = periodic_peak(x, np.cos(x*2*np.pi/period))
                self.assertGreater(peak, .9)

    def test_slow_nonrepeating_drape_has_no_periodic_peak(self):
        x = np.arange(600)*.001
        peak, _ = periodic_peak(x, np.cos(x*2*np.pi/1.2))
        self.assertEqual(peak, 0.)

    def test_linear_slope_and_constant_have_no_periodicity(self):
        x = np.arange(600)*.001
        for height in [x*.1+1, np.ones(600)]:
            self.assertEqual(periodic_peak(x, height)[0], 0.)

    def test_uncorrelated_irregular_edge_is_not_periodic(self):
        x = np.arange(600)*.001
        peak, _ = periodic_peak(x, np.random.default_rng(95).normal(size=600))
        self.assertLess(peak, .3)


if __name__ == '__main__':
    unittest.main()
