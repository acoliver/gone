"""Controls for the visible sofa gash measurements, independent of Blender."""
from pathlib import Path
import sys
import unittest

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_pass11_metrics import cloth_coverage, visible_gashes


class VisibleGashTests(unittest.TestCase):
    def test_antialiased_cloth_fringe_mix_is_not_a_new_hole(self):
        rgb = np.zeros((80, 100, 3), dtype=np.uint8)
        rgb[10:70, 10:90] = (255, 0, 0)
        rgb[25:55, 40:43] = (127, 127, 0)
        mask = cloth_coverage(rgb)
        self.assertTrue(mask[25:55, 40:43].all())
        self.assertEqual(visible_gashes(mask, []), [])

    def test_constant_width_slot_is_still_rejected_at_twelve_pixels(self):
        mask = np.zeros((180, 220), bool)
        mask[10:170, 10:210] = True
        mask[70:100, 40:180] = False
        seeds = np.array([[[70, 40], [70, 180]], [[100, 40], [100, 180]]])
        values = visible_gashes(mask, seeds)
        self.assertTrue(values)
        self.assertGreater(max(v['longest_straight_run_px'] for v in values), 12)
        self.assertTrue(any(v['width_cv'] is not None for v in values))

    def test_open_gash_is_measured_without_inventing_a_closing_edge(self):
        mask = np.zeros((180, 220), bool)
        mask[10:170, 10:210] = True
        mask[70:100, :180] = False
        seeds = np.array([[[70, 10], [70, 180]], [[100, 10], [100, 180]]])
        values = visible_gashes(mask, seeds)
        self.assertTrue(values)
        self.assertGreater(max(v['longest_straight_run_px'] for v in values), 12)
        self.assertTrue(any(not v['closed'] for v in values))

    def test_other_object_silhouette_is_not_a_cloth_lip(self):
        rgb = np.array([[[255, 0, 255], [255, 255, 255], [0, 0, 255], [255, 0, 0], [0, 255, 0]]], dtype=np.uint8)
        np.testing.assert_array_equal(cloth_coverage(rgb), [[False, False, False, True, True]])


if __name__ == '__main__':
    unittest.main()
