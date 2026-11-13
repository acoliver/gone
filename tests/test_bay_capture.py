"""Regression tests for the bay circuit image checks."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_bay_capture import check, white_squares


class BayCaptureTest(unittest.TestCase):
    def test_solid_white_squares_are_rejected(self):
        pixels = np.zeros((100, 100, 3), dtype=np.uint8)
        pixels[10:30, 20:40] = 255
        self.assertEqual(white_squares(pixels), [([10, 20], [29, 39])])

    def test_narrow_strip_is_not_a_square(self):
        pixels = np.zeros((100, 100, 3), dtype=np.uint8)
        pixels[10:60, 20:25] = 255
        self.assertEqual(white_squares(pixels), [])

    def test_red_wash_fails_and_quiescent_grey_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            for circuit in ['emergency-red-orange', 'secondary-white']:
                Image.new('RGB', (2304, 1296), (50, 38, 34)).save(Path(directory) / (circuit + '-bay.png'))
            self.assertEqual(check(directory), [])
            Image.new('RGB', (2304, 1296), (125, 44, 34)).save(Path(directory) / 'emergency-red-orange-bay.png')
            self.assertTrue(any('red wash' in failure for failure in check(directory)))


if __name__ == '__main__':
    unittest.main()
