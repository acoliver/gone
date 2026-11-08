"""Image-derived locker colour, calibration and physical projection contracts."""
import unittest

import numpy as np
from PIL import Image

from locker_swatches import paint_field, project_swatch, calibrate, class_scores, edge_variation


class LockerSwatchTests(unittest.TestCase):
    def test_uses_the_hatch_chroma_rule(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from prepare_hatch_paint import paint_fields
        image = Image.fromarray(np.array([[[100, 120, 110], [110, 45, 20], [70, 70, 70]]], np.uint8))
        colour, expected = paint_fields(image)
        np.testing.assert_allclose(paint_field(colour), expected)

    def test_runoff_is_short_translucent_and_physically_narrow(self):
        from streak_sources import source_rows
        sources = [dict(part='Rivets', position_blender=[i * .03, -.3, 2.1]) for i in range(20)]
        points, shapes = source_rows(sources, 9501)
        self.assertTrue(((points[:, 3] >= .004) & (points[:, 3] <= .012)).all())
        self.assertTrue(((shapes[:, 0] >= .060) & (shapes[:, 0] <= .200)).all())
        self.assertLess(float(shapes[:, 1].max()), 1.)
        np.testing.assert_array_equal(source_rows(sources, 9501), [points, shapes])

    def test_projection_keeps_300_pixels_per_metre_on_each_plane(self):
        yy, xx = np.mgrid[:768, :768]
        image = np.stack([xx / 768, yy / 768, np.zeros_like(xx)], -1)
        points = np.array([[.1, -.3, .2], [.2, -.3, .2], [.1, -.3, .3]])
        normal = np.tile([0, -1, 0], (3, 1))
        result = project_swatch(image, points, normal)
        self.assertAlmostEqual(result[1, 0] - result[0, 0], 30 / 768)
        self.assertAlmostEqual(result[2, 1] - result[0, 1], 30 / 768)
        top = project_swatch(image, points[:, [0, 2, 1]], normal[:, [0, 2, 1]])
        np.testing.assert_allclose(top - top[0], result - result[0])

    def test_calibration_multiplies_linear_light_not_srgb(self):
        image = np.full((10, 10, 3), .5)
        result = calibrate(image, [2, 1, .5])
        np.testing.assert_allclose(result[0, 0], [.6858361, .5, .3607802], atol=1e-6)

    def test_class_scores_reject_chroma_shift_and_accept_identical_colour(self):
        image = np.zeros((40, 40, 3))
        image[:20] = [.45, .50, .46]
        image[20:] = [.42, .20, .08]
        score = class_scores(image, image)
        self.assertLess(max(score.values()), 1e-6)
        changed = image.copy()
        changed[20:] = [.65, .20, .08]
        self.assertGreater(class_scores(changed, image)['rust_mean_delta_e'], 8)

    def test_flattening_removes_a_baked_light_gradient_without_changing_chroma(self):
        from locker_swatches import flatten_lighting
        from colour import srgb
        yy, xx = np.mgrid[:64, :64]
        energy = np.ones((64, 64, 3)) * [.12, .10, .08]
        illuminated = srgb(energy * np.exp((xx / 64 - .5) * .8)[..., None])
        flat = flatten_lighting(illuminated)
        self.assertLess(float(flat.std((0, 1)).max()), 1e-6)
        np.testing.assert_allclose(flat[0, 0], srgb(energy)[0, 0], atol=1e-6)

    def test_edge_reach_uses_image_variation_instead_of_a_constant_geometry_inset(self):
        from locker_swatches import edge_reach
        reference = np.repeat(np.linspace(.2, .5, 100).reshape(10, 10, 1), 3, axis=2)
        samples = np.array([[.2, .1, .08], [.35, .15, .1], [.5, .2, .1]])
        reach = edge_reach(samples, reference)
        self.assertGreater(float(np.ptp(reach)), .015)
        self.assertTrue(((reach >= .005) & (reach <= .025001)).all())

    def test_continuous_edge_outline_has_zero_variation(self):
        self.assertEqual(edge_variation(np.ones(20)), 0)
        self.assertGreater(edge_variation(np.tile([0, 1], 10)), .35)


if __name__ == '__main__':
    unittest.main()
