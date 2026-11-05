"""Numerical generated-paint preprocessing contracts, without image judgment."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

spec = importlib.util.spec_from_file_location("paint", Path(__file__).resolve().parents[1] / "tools/prepare_hatch_paint.py")
paint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paint)


class HatchPaintTest(unittest.TestCase):
    def test_crop_preserves_square_texels_instead_of_stretching(self):
        image = Image.new("RGB", (100, 200), "black")
        image.paste("white", (40, 90, 60, 110))
        result = np.asarray(paint.crop_resize(image, (100, 100)))[:, :, 0]
        ys, xs = np.where(result > 200)
        self.assertEqual(xs.max() - xs.min(), ys.max() - ys.min())

    def test_paint_separation_raises_grey_green_sheets_over_brown_rust(self):
        image = Image.new("RGB", (2, 1))
        image.putdata([(110, 115, 100), (110, 45, 15)])
        _, mask = paint.paint_fields(image)
        self.assertGreater(mask[0, 0], .9)
        self.assertLess(mask[0, 1], .1)
        self.assertTrue(np.isfinite(mask).all())

    def test_front_back_frame_are_separate_cells_with_derived_height(self):
        atlas, fields = paint.pack(Image.new("RGB", (100, 220), (100, 110, 100)),
                                   Image.new("RGB", (100, 220), (110, 45, 15)),
                                   Image.new("RGB", (100, 220), (90, 100, 90)))
        self.assertEqual(atlas.size, (1024, 2048))
        pixels = np.asarray(atlas)
        np.testing.assert_array_equal(pixels[500, 250, :3], [100, 110, 100])
        np.testing.assert_array_equal(pixels[500, 750, :3], [110, 45, 15])
        np.testing.assert_array_equal(pixels[1500, 500, :3], [90, 100, 90])
        self.assertGreater(pixels[500, 250, 3], pixels[500, 750, 3])
        self.assertEqual([field.shape for field in fields], [(1088, 512), (1088, 512), (960, 1024)])


if __name__ == "__main__":
    unittest.main()
