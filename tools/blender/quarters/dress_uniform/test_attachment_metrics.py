"""An authored fitting base remains identifiable after rotation and deformation."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from attachment_metrics import base_indices, rigid_normal


class AttachmentMetricsTest(unittest.TestCase):
    def test_authored_base_is_not_pose_dependent(self):
        base = np.array([[-.01, 0, -.01], [.01, 0, -.01], [0, 0, .01]])
        original = np.vstack([base+[0, -.001, 0], base])
        indices = base_indices(original, base)
        np.testing.assert_array_equal(indices, [3, 4, 5])
        rotation = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]])
        destination = original@rotation+[.3, .4, .5]
        np.testing.assert_allclose(rigid_normal(original, destination, indices, [0, -1, 0]),
                                   [1, 0, 0], atol=1e-10)

    def test_wrong_topology_fails(self):
        with self.assertRaisesRegex(ValueError, 'no matching vertex'):
            base_indices([[0, 0, 0], [1, 0, 0]], [[0, .001, 0]])

    def test_duplicate_anchor_fails(self):
        with self.assertRaisesRegex(ValueError, 'multiple anchors'):
            base_indices([[0, 0, 0], [1, 0, 0]], [[0, 0, 0], [0, 0, 0]])


if __name__ == '__main__':
    unittest.main()
