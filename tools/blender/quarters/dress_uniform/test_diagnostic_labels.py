"""Antialiased opaque materials must not create synthetic cloth openings."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'quarters_aging'))
from diagnostic_labels import decode_labels
from seat_image_gates import opening_metrics


class Labels(unittest.TestCase):
    def test_material_mixtures_are_continuous(self):
        for color in [(255, 0, 128), (128, 128, 0), (128, 128, 128)]:
            image = np.zeros((100, 100, 3), np.uint8)
            image[10:90, 10:90] = (255, 0, 0)
            image[20:80, 49:51] = color
            labels = decode_labels(image)
            self.assertTrue((labels[10:90, 10:90] != 0).all(), color)
            self.assertEqual(opening_metrics(labels != 0), [])

    def test_fittings_are_not_fringe(self):
        image = np.array([[(255, 0, 0), (0, 255, 0), (255, 0, 255),
                           (255, 255, 255), (255, 0, 128), (0, 0, 255), (0, 0, 0)]], dtype=np.uint8)
        np.testing.assert_array_equal(decode_labels(image), [[1, 2, 5, 4, 5, 0, 0]])

    def test_true_openings_and_hanger_are_not_filled(self):
        image = np.full((100, 100, 3), (255, 0, 0), np.uint8)
        image[20:80, 40:45] = 0
        image[20:80, 45:50] = (0, 0, 255)
        labels = decode_labels(image)
        self.assertFalse(labels[20:80, 40:50].any())
        openings = opening_metrics(labels != 0)
        self.assertEqual(len(openings), 1)
        self.assertGreater(openings[0]['longest_straight_run_px'], 12)


if __name__ == '__main__':
    unittest.main()
