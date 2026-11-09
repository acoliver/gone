"""Exterior-connected tears must receive the same lip tests as enclosed tears."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lip_metrics import contour_runs, gap_width_cv, polyline_metrics


class LipMetrics(unittest.TestCase):
    def test_open_straight_lip_is_rejected(self):
        points = np.c_[np.arange(150.), np.full(150, 30.)]
        result = polyline_metrics(points)
        self.assertGreater(result['longest_straight_run_px'], 12)
        self.assertLess(result['contour_dimension'], 1.15)
        self.assertGreaterEqual(result['length_px'], 64)

    def test_width_uses_opposing_lips(self):
        a = np.c_[np.arange(180.), np.zeros(180)]
        uniform = a+[0, 10]
        varied = a.copy()
        varied[:, 1] = 12+9*np.sin(np.arange(180.)/27)
        self.assertLess(gap_width_cv(a, uniform), .01)
        self.assertGreater(gap_width_cv(a, varied), .35)

    def test_exterior_and_enclosed_lips_are_both_traceable(self):
        for exterior in [False, True]:
            cloth = np.zeros((240, 240), bool)
            cloth[10:230, 10:230] = True
            cloth[80:160, 100:125 if not exterior else 240] = False
            seed = np.array([[80., 100.], [159., 100.]])
            runs = contour_runs(cloth, [seed], radius=3.)
            self.assertTrue(runs, exterior)
            self.assertGreater(max(polyline_metrics(r)['length_px'] for r in runs), 64)

    def test_unrelated_outline_is_not_a_tear(self):
        cloth = np.zeros((200, 200), bool)
        cloth[20:180, 20:180] = True
        self.assertEqual(contour_runs(cloth, [np.array([[50, 90], [150, 90]])], 3), [])


if __name__ == '__main__':
    unittest.main()
