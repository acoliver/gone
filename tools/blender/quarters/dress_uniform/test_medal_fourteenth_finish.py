"""Generated medal geometry and photographic enamel processing."""
import unittest
import numpy as np
from medal_fourteenth_finish import (
    boundary_radius, radial_transfer, remove_achromatic_highlights, visible_star_transfer,
    enamel_coat_map,
)


class FourteenthFinishTests(unittest.TestCase):
    def test_coat_covers_new_enamel_outside_old_transport_mask(self):
        existing = np.full((4, 3), .1)
        weight = np.array([.2, .6, 1., 0.])
        transported = np.array([False, False, True, False])
        front = np.array([True, True, True, False])
        present = enamel_coat_map(existing, weight, transported, front, 0.)
        np.testing.assert_array_equal(present[:3], np.zeros((3, 3)))
        np.testing.assert_array_equal(present[3], existing[3])
        remembered = enamel_coat_map(existing, weight, transported, front, .01)
        np.testing.assert_allclose(remembered[:3, 0], [.002, .006, .01])

    def test_clipped_star_tip_scales_its_visible_relief_and_pins_bezel(self):
        q = np.array([[0., -.002, .0115], [0., -.002, .012],
                      [0., -.002, .013], [0., .001, .010]])
        result = visible_star_transfer(q, np.full(4, .014), np.full(4, .01158), .012)
        self.assertAlmostEqual(result[0, 2], .0115 * .965)
        np.testing.assert_array_equal(result[1:], q[1:])
        np.testing.assert_array_equal(result[:, 1], q[:, 1])

    def test_highlight_removal_preserves_diffuse_chromatic_difference(self):
        diffuse = np.array([.004, .020, .100])
        rgb = diffuse + np.array([0., 0., .02, .08])[:, None]
        corrected, floor = remove_achromatic_highlights(rgb, np.ones(4, dtype=bool))
        self.assertAlmostEqual(floor, .004)
        np.testing.assert_allclose(corrected, np.tile(diffuse, (4, 1)))
        np.testing.assert_allclose(corrected[:, 2] - corrected[:, 1], .080)

    def test_highlight_floor_excludes_unrelated_reference_materials(self):
        rgb = np.array([[.004, .020, .100], [.004, .020, .100], [1., .8, .6]])
        _, floor = remove_achromatic_highlights(rgb, np.array([True, True, False]))
        self.assertAlmostEqual(floor, .004)

    def test_boundary_sampling_at_vertices_and_between_edges(self):
        outline = np.array([[0., 2.], [2., 0.], [0., -2.], [-2., 0.]])
        angles = np.array([0., np.pi / 4, np.pi / 2, np.pi, 3 * np.pi / 2])
        np.testing.assert_allclose(boundary_radius(outline, angles),
                                   [2., np.sqrt(2), 2., 2., 2.])

    def test_star_scales_and_surrounding_field_extends(self):
        q = np.array([[0., -.002, .008], [0., -.001, .010],
                      [0., -.001, .012], [0., .001, .008]])
        result = radial_transfer(q, np.full(4, .010), np.full(4, .009), .012)
        np.testing.assert_allclose(result[:, 2], [.0072, .009, .012, .008])
        np.testing.assert_array_equal(result[:, 1], q[:, 1])
        np.testing.assert_array_equal(result[:, 0], q[:, 0])

    def test_monotone_and_outer_hardware_unchanged(self):
        r = np.linspace(0, .020, 1001)
        q = np.c_[r, np.full(len(r), -.001), np.zeros(len(r))]
        result = radial_transfer(q, np.full(len(r), .014), np.full(len(r), .0115), .012)
        self.assertTrue(np.all(np.diff(result[:, 0]) > 0))
        np.testing.assert_array_equal(result[r >= .0144], q[r >= .0144])


if __name__ == '__main__':
    unittest.main()
