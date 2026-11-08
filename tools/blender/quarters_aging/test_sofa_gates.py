"""Controls for fail-closed pass-4 checks and deposition statistics."""
import unittest

import numpy as np
import trimesh

from sofa_gates import SPECS, cluster_fraction, dihedral_share, missing_gates, vertical_area


class SofaGates(unittest.TestCase):
    def test_all_required_checks_exist_and_unmeasured_is_not_success(self):
        expected = {f'G{i}' for i in [*range(1, 20), 30, 31, 32]}
        self.assertEqual(set(SPECS), expected)
        self.assertTrue(all(not g['pass'] and g['value'] is None for g in missing_gates().values()))

    def test_planar_cloth_has_no_sharp_dihedral(self):
        sheet = trimesh.Trimesh([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], [[0, 1, 2], [0, 2, 3]])
        self.assertEqual(dihedral_share(sheet), 0)
        self.assertEqual(vertical_area(sheet), 0)
        cube = trimesh.creation.box()
        self.assertGreater(dihedral_share(cube), .3)
        self.assertGreater(vertical_area(cube), 0)

    def test_cluster_rejects_compact_pile(self):
        rng = np.random.default_rng(95)
        self.assertEqual(cluster_fraction(rng.normal(0, .002, (100, 2))), 1.)
        points = np.array([[x, y] for x in np.arange(10)*.05 for y in np.arange(10)*.05])
        self.assertEqual(cluster_fraction(points), 0.)


if __name__ == '__main__':
    unittest.main()
