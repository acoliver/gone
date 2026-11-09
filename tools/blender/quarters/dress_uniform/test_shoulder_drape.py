"""A free shoulder tongue should roll slightly and bend down at its tip."""
import unittest

import numpy as np

from shoulder_drape import replacement_motion


class ShoulderDrapeTests(unittest.TestCase):
    def test_support_is_fixed(self):
        t = np.linspace(0, 1, 21)
        np.testing.assert_array_equal(replacement_motion(t, np.zeros_like(t)), np.zeros((21, 3)))
        np.testing.assert_array_equal(replacement_motion(np.zeros(3), np.ones(3)), np.zeros((3, 3)))

    def test_roll_is_small_and_tip_droops(self):
        t = np.linspace(0, 1, 101)
        motion = replacement_motion(t, np.ones_like(t))
        old_weight = t*t*(3-2*t)
        roll = .014*old_weight+motion[:, 2]
        self.assertLessEqual(roll.max(), .004001)
        self.assertAlmostEqual(roll[-1], -.003)
        self.assertTrue(np.all(np.diff(roll[-15:]) < 0))
        self.assertAlmostEqual(motion[-1, 0], .010)
        self.assertAlmostEqual(motion[-1, 1], -.016)


if __name__ == '__main__':
    unittest.main()
