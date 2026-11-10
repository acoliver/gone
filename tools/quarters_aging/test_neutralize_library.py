"""Palette correction must preserve oxide colour and the image's spatial layout."""
import unittest

import numpy as np
from PIL import Image

from neutralize_library import neutral_transform, apply
from steel_library import align_paint, mute_green
from locker_gates import hsv


class NeutralPaletteTests(unittest.TestCase):
    def test_uniform_transform_aligns_paint_and_keeps_oxide(self):
        pixels = np.array([[[100, 84, 76], [130, 60, 30]],
                           [[130, 60, 30], [100, 84, 76]]], np.uint8)
        target = np.array([.38, .46, .45])
        transform = neutral_transform(Image.fromarray(pixels), target)
        result = np.asarray(apply(Image.fromarray(pixels), transform), float)/255
        np.testing.assert_allclose(result[0, 0], target, atol=1/255)
        np.testing.assert_allclose(result[0, 1], pixels[0, 1]/255, atol=1/255)
        np.testing.assert_array_equal(result[0, 0], result[1, 1])
        np.testing.assert_array_equal(result[0, 1], result[1, 0])

    def test_soft_pigment_alignment_does_not_tint_oxide(self):
        image = Image.fromarray(np.array([[[100, 70, 70], [130, 60, 30]]], np.uint8))
        target = np.array([.38, .46, .45])
        result = np.asarray(align_paint(image, target), float)/255
        np.testing.assert_allclose(result[0, 0], target, atol=1/255)
        np.testing.assert_allclose(result[0, 1], [130/255, 60/255, 30/255], atol=1/255)

    def test_dark_byte_rounding_cannot_restore_saturated_green(self):
        result = np.asarray(mute_green(Image.new('RGB', (4, 4), (2, 3, 2))), float)/255
        hue, saturation, _ = hsv(result)
        self.assertFalse(np.any((hue >= 70) & (hue <= 170) & (saturation > .23)))

    def test_missing_oxide_is_rejected(self):
        with self.assertRaises(ValueError):
            neutral_transform(Image.new('RGB', (4, 4), (100, 100, 100)), np.array([.38, .46, .45]))


if __name__ == '__main__':
    unittest.main()
