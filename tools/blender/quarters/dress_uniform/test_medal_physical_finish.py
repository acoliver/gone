"""Physical conductor colour and resolved ribbon ribs, without changing stripe pigment."""
import unittest

import numpy as np

from medal_dry_finish import brass_finish, ribbon_weave


class PhysicalFinishTests(unittest.TestCase):
    def test_exposed_brass_retains_physical_reflectance(self):
        base = np.ones((8, 8, 3)) * [.66, .43, .14]
        rough = np.full((8, 8), .30)
        zero = np.zeros_like(rough)
        colour, finish, metal = brass_finish(base, rough, zero, zero, False)
        np.testing.assert_allclose(colour.mean((0, 1)), [.9, .64, .24], atol=1e-12)
        self.assertTrue(np.all((finish >= .3) & (finish <= .45)))
        self.assertTrue(np.all(metal >= .95))

    def test_dry_oxide_stays_conducting_and_brown_on_exposed_faces(self):
        base = np.ones((1, 3, 3)) * [.66, .43, .14]
        rough = np.full((1, 3), .30)
        cavity = np.array([[0., 0., 1.]])
        edge = np.array([[0., 1., 0.]])
        colour, finish, metal = brass_finish(base, rough, cavity, edge, True)
        self.assertGreaterEqual(metal[0, 0], .9)
        self.assertGreater(colour[0, 0, 0] / colour[0, 0, 1], 1.5)
        self.assertGreater(colour[0, 1].mean(), colour[0, 0].mean())
        self.assertGreater(colour[0, 0].mean(), colour[0, 2].mean())
        self.assertGreater(finish[0, 0], .4)
        self.assertGreater(finish[0, 2], finish[0, 0])

    def test_ribbon_has_directional_ribs_in_normal_and_roughness(self):
        normal, rough, fibre = ribbon_weave()
        np.testing.assert_allclose(np.linalg.norm(normal, axis=2), 1, atol=1e-12)
        self.assertGreater(np.ptp(normal[:, :, 1]), .4)
        self.assertGreater(np.ptp(rough), .15)
        self.assertGreater(np.std(np.diff(normal[:, :, 1], axis=0)), 2 * np.std(np.diff(normal[:, :, 1], axis=1)))
        self.assertGreater(fibre.min(), .9)
        self.assertLessEqual(fibre.max(), 1.)


if __name__ == '__main__':
    unittest.main()
