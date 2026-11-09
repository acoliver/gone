import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/blender/quarters/sofa'))
from finish_calibration import update_albedo, calibrated_scan
from uv_metrics import measure


class SofaFinish(unittest.TestCase):
    def test_calibration_updates_in_linear_light(self):
        result = update_albedo(np.array([.2, .3, .4]), np.array([128, 128, 128]), np.array([64, 64, 64]))
        np.testing.assert_allclose(result, [.0475024, .0712536, .0950048], atol=.0000001)

    def test_calibrated_scan_preserves_linear_mean_and_grain(self):
        scan = np.linspace(.2, .7, 24).reshape(2, 4, 3)
        target = np.array([.12, .08, .03])
        from finish_materials import linear
        result = calibrated_scan(scan, target)
        np.testing.assert_allclose(linear(result).mean((0, 1)), target, atol=1e-6)
        self.assertGreater(result.std(), .03)

    def test_uv_measure_rejects_stacked_triangles(self):
        uv = np.array([[[0, 0], [1, 0], [0, 1]]] * 2, dtype=float)
        xyz = np.dstack([uv, np.zeros((2, 3))])
        self.assertGreater(measure(uv, xyz, 64)['overlap_fraction'], .99)

    def test_uv_measure_reports_isotropic_disjoint_charts(self):
        uv = np.array([[[0, 0], [.4, 0], [0, .4]], [[.6, .6], [1, .6], [.6, 1]]])
        xyz = np.dstack([uv, np.zeros((2, 3))])
        result = measure(uv, xyz, 64)
        self.assertEqual(result['overlap_fraction'], 0)
        self.assertAlmostEqual(result['anisotropy_median'], 1)


if __name__ == '__main__':
    unittest.main()
