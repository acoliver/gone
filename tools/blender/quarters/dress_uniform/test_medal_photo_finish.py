"""Medal-local photo calibration retains metal and uses physical-scale dry oxide."""
import unittest

import numpy as np

from medal_photo_finish import calibrated_brass, oxide_field


class PhotoFinishTests(unittest.TestCase):
    def test_dry_oxide_is_deterministic_in_surface_coordinates(self):
        y, x = np.mgrid[:128, :128]
        position = np.stack([x / 4000, np.zeros_like(x), y / 4000], -1)
        first = oxide_field(position)
        np.testing.assert_array_equal(first, oxide_field(position.copy()))
        self.assertGreater(np.std(first), .15)
        self.assertGreaterEqual(first.min(), -1)
        self.assertLessEqual(first.max(), 1)
        # Sampling another UV chart at the same physical point must agree exactly.
        np.testing.assert_array_equal(first[::3, ::3], oxide_field(position[::3, ::3]))

    def test_finish_keeps_conducting_faces_and_deeper_recesses(self):
        cavity = np.array([[0., 0., 1.]])
        edge = np.array([[0., 1., 0.]])
        noise = np.zeros_like(cavity)
        for aged in [False, True]:
            colour, rough, metal = calibrated_brass(cavity, edge, noise, aged)
            self.assertTrue(np.all((colour >= 0) & (colour <= 1)))
            self.assertTrue(np.all((rough > 0) & (rough <= 1)))
            self.assertGreaterEqual(metal[0, 0], .9)
            self.assertGreater(colour[0, 1].mean(), colour[0, 2].mean())
            self.assertGreater(colour[0, 0].mean(), colour[0, 2].mean())
            self.assertGreaterEqual(rough[0, 2], rough[0, 1])

    def test_present_oxide_has_more_face_variation_than_remembered(self):
        noise = np.linspace(-1, 1, 64).reshape(8, 8)
        zero = np.zeros_like(noise)
        clean = calibrated_brass(zero, zero, noise, False)[0]
        aged = calibrated_brass(zero, zero, noise, True)[0]
        self.assertGreater(np.std(aged / aged.mean(0)), np.std(clean / clean.mean(0)))


if __name__ == '__main__':
    unittest.main()
