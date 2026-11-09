"""Pass-10 pilot retains pass-11 coverage and open-lip measurement behavior."""
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/blender/quarters_aging'))
from sofa_pass11_metrics import cloth_coverage, visible_gashes


class SofaPilotMetrics(unittest.TestCase):
    def test_antialiased_red_green_mixture_is_cloth(self):
        rgb = np.array([[[130, 125, 0], [0, 0, 0], [255, 0, 255]]])
        self.assertEqual(cloth_coverage(rgb).tolist(), [[True, False, False]])

    def test_exterior_gash_keeps_open_lips(self):
        cloth = np.ones((180, 180), dtype=bool)
        cloth[30:150, :70] = False
        segments = np.array([[[30, 0], [30, 70]], [[150, 0], [150, 70]]])
        outlines = visible_gashes(cloth, segments, radius=6)
        self.assertTrue(outlines)
        self.assertTrue(all(not item['closed'] for item in outlines))
        self.assertGreater(max(item['longest_straight_run_px'] for item in outlines), 12)


if __name__ == '__main__':
    unittest.main()
