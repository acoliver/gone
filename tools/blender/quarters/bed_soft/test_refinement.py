"""Controls for the aged-only finishing fields."""
import unittest
import numpy as np
from refinement_fields import convex_outline, powder_field, cloth_color


class RefinementTests(unittest.TestCase):
    def test_outline_retains_the_existing_plate_footprint(self):
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [.5, .5], [0, 0]])
        outline = convex_outline(points)
        self.assertEqual(len(outline), 4)
        following = np.roll(outline, -1, axis=0)
        area = (outline[:, 0] * following[:, 1] - outline[:, 1] * following[:, 0]).sum() / 2
        self.assertAlmostEqual(area, 1)

    def test_powder_has_a_deposit_and_a_soft_empty_margin(self):
        alpha = powder_field(95246, 256)
        y, x = np.mgrid[-1:1:256j, -1:1:256j]
        radius = np.hypot(x, y)
        self.assertGreater(alpha[radius < .45].mean(), .35)
        self.assertLess(alpha[radius > .96].max(), .01)
        self.assertGreater(np.mean((alpha > .05) & (alpha < .8)), .2)
        np.testing.assert_array_equal(alpha, powder_field(95246, 256))

    def test_folds_dark_and_dust_on_upward_faces_without_cream(self):
        color = cloth_color(np.array([0., 1., 1.]), np.array([0., 0., 1.]),
                            np.array([.5, .5, .5]), wool=False)
        self.assertTrue(np.all(color[0] < color[1]))
        self.assertGreater(color[2].mean(), color[1].mean())
        self.assertLess(color.max(), .26)
        self.assertTrue(np.all(color[:, 0] > color[:, 1]))
        self.assertTrue(np.all(color[:, 1] > color[:, 2]))


if __name__ == '__main__':
    unittest.main()
