"""A sideways thin ellipse must not pass the camera-visible pressed-sleeve gate."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sleeve_metrics import section_ratio


class SleeveSections(unittest.TestCase):
    def test_visible_flat_section_passes(self):
        t = np.linspace(0, 2*np.pi, 1000)
        points = np.c_[.05*np.cos(t), .01*np.sin(t), np.zeros(len(t))]
        self.assertLess(section_ratio(points, [0, 0, 1], [0, -1, 0])['ratio'], .45)

    def test_edge_on_flat_section_fails(self):
        t = np.linspace(0, 2*np.pi, 1000)
        points = np.c_[.01*np.cos(t), .05*np.sin(t), np.zeros(len(t))]
        self.assertGreater(section_ratio(points, [0, 0, 1], [0, -1, 0])['ratio'], .45)

    def test_sampling_density_does_not_change_extent(self):
        points = np.array([[.05, 0, 0], [0, .01, 0], [-.05, 0, 0], [0, -.01, 0]])
        biased = np.vstack([points, np.repeat(points[:1], 100, axis=0)])
        self.assertEqual(section_ratio(points, [0, 0, 1]), section_ratio(biased, [0, 0, 1]))


if __name__ == '__main__':
    unittest.main()
