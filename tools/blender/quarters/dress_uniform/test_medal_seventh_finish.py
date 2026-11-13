"""#130 dry oxide stays in recesses and is removed from convex rims."""
import unittest

import numpy as np

from medal_seventh_finish import recess_oxide


class RecessOxideTests(unittest.TestCase):
    def test_clean_exposed_faces_have_no_blanket_oxide(self):
        np.testing.assert_array_equal(recess_oxide(np.zeros(8),np.zeros(8),np.ones(8)),np.zeros(8))

    def test_measured_cavity_and_occlusion_each_localize_oxide(self):
        oxide = recess_oxide(np.array([0.,1.,0.]),np.zeros(3),np.array([1.,1.,.2]))
        self.assertEqual(oxide[0],0)
        self.assertGreater(oxide[1],.8)
        self.assertGreater(oxide[2],.8)

    def test_convex_rim_rejects_mottled_cavity_signal(self):
        oxide = recess_oxide(np.ones(2),np.array([0.,1.]),np.zeros(2))
        self.assertLess(oxide[1],oxide[0]*.05)


if __name__ == '__main__':
    unittest.main()
