"""Photometric measurements must separate exposure from colour and spatial scale."""
import unittest

import numpy as np

from medal_photo_measure import band_contrast, chroma_hue, reference_masks, targets


class PhotoMeasureTests(unittest.TestCase):
    def test_chroma_and_hue_are_exposure_invariant(self):
        samples = np.tile([.4, .24, .09], (100, 1))
        np.testing.assert_allclose(chroma_hue(samples), chroma_hue(samples * .2), atol=1e-10)

    def test_texture_band_is_exposure_invariant(self):
        y, x = np.mgrid[:256, :256]
        lum = .2 + .02 * np.sin(x * 2 * np.pi / 12)
        mask = np.ones_like(lum, bool)
        self.assertAlmostEqual(band_contrast(lum, mask, 16, .5, 2),
                               band_contrast(lum * .4, mask, 16, .5, 2))
        self.assertGreater(band_contrast(lum, mask, 16, .5, 2), .01)
        self.assertLess(band_contrast(np.ones_like(lum), mask, 16, .5, 2), 1e-10)

    def test_segmentation_uses_pendant_geometry_not_warm_background(self):
        y, x = np.mgrid[:864, :1536]
        radius = np.hypot((x - 780) / 245, (y - 540) / 240)
        rgb = np.full((864, 1536, 3), [.2, .25, .3])
        rgb[radius < 1] = [.6, .45, .2]
        rgb[radius < .7] = [.03, .08, .25]
        # A star-like metal core and dark engraved annulus provide nonempty regions.
        rgb[(abs(x - 780) < 60) & (abs(y - 540) < 100)] = [.6, .45, .2]
        rgb[(radius > .83) & (radius < .85)] = [.25, .15, .04]
        masks, scale, geometry = reference_masks(rgb)
        np.testing.assert_allclose(geometry['ellipse_cx_cy_rx_ry_shear'][:4], [780, 540, 245, 240], atol=2)
        self.assertAlmostEqual(scale, 490 / 32, delta=.1)
        for name, mask in masks.items():
            self.assertTrue(mask.any(), name)
        self.assertFalse(np.any(masks['brass'] & masks['wool']))
        self.assertFalse(np.any(masks['enamel'] & masks['brass']))


if __name__ == '__main__':
    unittest.main()
