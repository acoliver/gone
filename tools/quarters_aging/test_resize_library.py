"""Resizing never trades the density floor for texture savings."""
import unittest

from resize_library import density_after_resize


class AtlasResizeTests(unittest.TestCase):
    def test_resolution_scales_the_weakest_uv_direction(self):
        self.assertAlmostEqual(density_after_resize(800.4, 4096, 3072), 600.3)
        self.assertAlmostEqual(density_after_resize(1087.8, 4096, 2560), 679.875)

    def test_rejects_half_size_below_six_hundred(self):
        for density in (800.4, 848.9, 1087.8):
            with self.assertRaisesRegex(ValueError, '600'):
                density_after_resize(density, 4096, 2048)
        with self.assertRaises(ValueError):
            density_after_resize(800.4, 4096, 0)


if __name__ == '__main__':
    unittest.main()
