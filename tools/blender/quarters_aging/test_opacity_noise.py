"""Blender controls for a continuous breakup field on axis-aligned cloth."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from opacity_bake import value_noise


class OpacityNoise(unittest.TestCase):
    def test_axis_aligned_fabric_does_not_erase_the_noise(self):
        points = np.c_[np.linspace(-.02, .02, 1000), np.zeros(1000), np.zeros(1000)]
        a = value_noise(points, .002, 9501)
        self.assertGreater(a.std(), .2)
        np.testing.assert_array_equal(a, value_noise(points, .002, 9501))
        self.assertFalse(np.array_equal(a, value_noise(points, .002, 9502)))

    def test_noise_is_continuous_across_a_lattice_plane(self):
        points = np.array([[.002-1e-9, .001, .0004], [.002+1e-9, .001, .0004]])
        values = value_noise(points, .002, 9501)
        self.assertLess(abs(values[0]-values[1]), 1e-5)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
