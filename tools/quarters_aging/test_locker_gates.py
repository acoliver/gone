"""Negative controls for the capture classifiers. Run with local Hunyuan Python."""
import unittest
import numpy as np
from locker_gates import hsv, newly_green, rust_pixels


class CaptureGateTests(unittest.TestCase):
    def test_grey_green_design_paint_is_not_rust(self):
        paint = np.full((100, 100, 3), [.473, .575, .556])
        self.assertFalse(rust_pixels(paint).any())
        self.assertEqual(newly_green(paint, paint, np.ones((100, 100), bool)), (0, 0))

    def test_new_green_patch_fails_but_existing_green_does_not(self):
        clean = np.full((100, 100, 3), [.473, .575, .556])
        aged = clean.copy()
        aged[20:30, 20:30] = [.1, .65, .15]
        prop = np.ones((100, 100), bool)
        area, _ = newly_green(clean, aged, prop)
        self.assertGreaterEqual(area, .005)
        self.assertEqual(newly_green(aged, aged, prop), (0, 0))

    def test_background_green_is_excluded(self):
        clean = np.full((100, 100, 3), .4)
        aged = clean.copy()
        aged[:10] = [.1, .7, .1]
        prop = np.ones((100, 100), bool)
        prop[:10] = False
        self.assertEqual(newly_green(clean, aged, prop), (0, 0))

    def test_orange_brown_rust_detects_and_clean_steel_rejects(self):
        self.assertTrue(rust_pixels(np.array([[[.45, .19, .06]]])).item())
        self.assertFalse(rust_pixels(np.array([[[.56, .59, .59]]])).item())

    def test_hue_boundaries_and_achromatic_pixels(self):
        hue, saturation, _ = hsv(np.array([[[1., 0, 0], [0, 1., 0], [0, 0, 1.], [.5, .5, .5]]]))
        np.testing.assert_allclose(hue, [[0, 120, 240, 0]])
        self.assertEqual(saturation[0, 3], 0)


if __name__ == "__main__":
    unittest.main()
