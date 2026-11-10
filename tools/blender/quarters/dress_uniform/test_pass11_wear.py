"""Pass-eleven wear remains small, irregular and bounded away from fittings."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wear_pass11 import body_wear, lip_loss, wool_displacement


class Pass11Wear(unittest.TestCase):
    def test_fading_is_distributed_without_punching_new_holes(self):
        pattern = np.array([[.18, .4], [.28, .7], [1.3, .6], [.6, .8]])
        wear = body_wear(pattern)
        self.assertFalse(wear['hole'].any())
        self.assertTrue((wear['fade'] >= .03).all())
        self.assertTrue((wear['fade'] <= .35).all())
        self.assertGreater(np.ptp(wear['fade']), .04)

    def test_curled_bundle_atlas_is_deterministic_and_soft_edged(self):
        from soft_wool_atlas import bundle_alpha
        alpha = bundle_alpha(9521)
        np.testing.assert_array_equal(alpha, bundle_alpha(9521))
        self.assertEqual(alpha.shape, (1024, 1024))
        self.assertTrue(np.isfinite(alpha).all())
        self.assertGreater(np.sum((alpha > 0) & (alpha < 1)), 1000)
        self.assertGreater(alpha.mean(), .08)
        self.assertLess(alpha.mean(), .4)

    def test_lip_loss_varies_with_arclength_and_stays_within_support(self):
        station = np.linspace(0., .12, 1201)
        self.assertGreater(np.std(lip_loss(station, .012)), .0003)
        depth = np.linspace(.0002, .008, len(station))
        loss = lip_loss(station, depth)
        self.assertTrue((loss >= 0.).all())
        self.assertTrue((loss <= depth*.35+1e-12).all())

    def test_patch_is_wider_and_shorter_than_a_cut_slit(self):
        u, v = np.meshgrid(np.linspace(.105, .135, 301), np.linspace(.36, .40, 401))
        pattern = np.c_[u.ravel(), v.ravel()]
        result = body_wear(pattern)
        hole = pattern[result['hole']]
        self.assertGreater(len(hole), 50)
        ratio = np.ptp(hole, axis=0)[1]/np.ptp(hole, axis=0)[0]
        self.assertLess(ratio, 2.8)
        self.assertGreater(np.ptp(hole[:, 0]), .007)
        self.assertGreater(np.sum((result['thinning'] > .15) & ~result['hole']), len(hole))

    def test_no_losses_in_collar_or_sleeve(self):
        pattern = np.array([[.12, .94], [1.2, .38], [.37, .82], [.4, .02]])
        self.assertFalse(body_wear(pattern)['hole'].any())

    def test_wool_motion_bounded_and_fittings_retained(self):
        x, z = np.meshgrid(np.linspace(-.25, .25, 50), np.linspace(-.85, -.15, 60))
        points = np.c_[x.ravel(), np.zeros(x.size), z.ravel()]
        pattern = np.c_[np.full(x.size, .25), np.full(x.size, .5)]
        delta = wool_displacement(points, pattern)
        self.assertLessEqual(np.linalg.norm(delta, axis=1).max(), .0025)
        self.assertGreater(np.std(delta[:, 1]), .0001)
        np.testing.assert_array_equal(delta[points[:, 2] > -.36], 0)
        np.testing.assert_array_equal(delta[abs(points[:, 0]) < .03], 0)


if __name__ == '__main__':
    unittest.main()
