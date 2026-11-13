"""Large upward faces retain fine powder without magnifying cloudy paint."""
import unittest

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from settled_dust import soften_dust
from locker_faces import paint_fields


class SettledDustTests(unittest.TestCase):
    def test_reduces_clouds_preserves_fine_detail_and_leaves_corrosion_unchanged(self):
        yy, xx = np.mgrid[:256, :512]
        cloud = 18*np.sin(xx/48)*np.cos(yy/40)
        fine = 3*np.sin(xx*1.8)*np.cos(yy*1.6)
        rgb = np.stack([132+cloud+fine, 140+cloud+fine, 130+cloud+fine], -1)
        rgb[:20] = [85, 35, 20]
        source = Image.fromarray(np.uint8(np.round(rgb)))
        output = soften_dust(source, [1.6, .7])
        before, after = np.asarray(source, float), np.asarray(output, float)
        np.testing.assert_array_equal(after[:20], before[:20])
        a, b = before[50:-20, 30:-30].mean(-1), after[50:-20, 30:-30].mean(-1)
        self.assertLess(gaussian_filter(b, 8).std(), gaussian_filter(a, 8).std()*.3)
        self.assertGreater((b-gaussian_filter(b, 2)).std(), (a-gaussian_filter(a, 2)).std()*.5)
        self.assertLess(abs(a.mean()-b.mean()), 4)
        self.assertTrue(np.isfinite(after).all())
        self.assertEqual(output.size, source.size)
        np.testing.assert_array_equal(paint_fields(source)[1] < .5, paint_fields(output)[1] < .5)

    def test_requires_physical_dimensions_and_a_painted_source(self):
        with self.assertRaises(ValueError):
            soften_dust(Image.new('RGB', (32, 32), (132, 140, 130)), [0, 1])
        with self.assertRaises(ValueError):
            soften_dust(Image.new('RGB', (32, 32), (85, 35, 20)), [1, 1])


if __name__ == '__main__':
    unittest.main()
