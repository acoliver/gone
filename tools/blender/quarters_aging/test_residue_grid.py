"""Balanced residue controls cover both sides without changing the height source."""
from pathlib import Path
import sys
import unittest

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from residue_grid import balanced_grid


class ResidueGridTests(unittest.TestCase):
    def test_closed_positive_volume_within_each_budget(self):
        for back, target in [(False, 700), (True, 400)]:
            v, f = balanced_grid(.62, .16 if back else .66,
                                 lambda p: .018+.005*np.sin(p[:, 0]*150)*np.cos(p[:, 1]*170), 9601, back)
            mesh = trimesh.Trimesh(v, f)
            self.assertTrue(mesh.is_watertight)
            self.assertTrue(mesh.is_winding_consistent)
            self.assertGreater(mesh.volume, 0)
            self.assertEqual(mesh.euler_number, 2)
            self.assertLessEqual(len(f), target)
            planar = mesh.facets_area[mesh.facets_area > .001].sum()/mesh.area
            self.assertLessEqual(planar, .05)

    def test_seed_changes_underside_without_changing_roof_samples(self):
        height = lambda p: np.full(len(p), .020)
        a, _ = balanced_grid(.62, .66, height, 9601)
        b, _ = balanced_grid(.62, .66, height, 9602)
        n = len(a)//2
        np.testing.assert_array_equal(a[:n], b[:n])
        self.assertGreater(np.max(np.abs(a[n:]-b[n:])), .001)

    def test_invalid_height_fails_at_boundary(self):
        with self.assertRaises(ValueError):
            balanced_grid(.62, .66, lambda p: np.full(len(p), np.nan), 9601)


if __name__ == '__main__':
    unittest.main()
