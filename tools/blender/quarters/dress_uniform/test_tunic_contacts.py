"""The hanger baseline never exempts changed cloth, fittings or cards."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tunic_contacts import contact_gate


class TunicContacts(unittest.TestCase):
    def setUp(self):
        self.baseline = {'self': {'Hanger': {'count': 28}}, 'pairs': {}}
        self.current = {'self': {'Hanger': {'count': 28}, 'TunicBody': {'count': 0}}, 'pairs': {}}
        self.hanger = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])

    def measure(self, geometry=None):
        return contact_gate(self.current, self.baseline, self.hanger,
                            self.hanger if geometry is None else geometry)

    def test_exact_hanger_and_zero_changed_contacts_pass(self):
        self.assertTrue(self.measure()['pass'])

    def test_new_card_pair_is_never_exempt(self):
        self.current['pairs']['Hanger/LongWoolFringe'] = {'count': 1}
        self.assertFalse(self.measure()['pass'])
        self.assertEqual(self.measure()['changed_intersections'], 1)

    def test_changed_self_contacts_are_never_exempt(self):
        self.current['self']['TunicBody']['count'] = 1
        self.assertFalse(self.measure()['pass'])

    def test_hanger_contact_count_must_match(self):
        self.current['self']['Hanger']['count'] = 27
        self.assertFalse(self.measure()['pass'])

    def test_equal_contact_counts_do_not_prove_unchanged_hanger(self):
        moved = self.hanger.copy()
        moved[0, 0, 0] = .000001
        result = self.measure(moved)
        self.assertFalse(result['pass'])
        self.assertFalse(result['hanger_geometry_exact'])

    def test_triangle_and_vertex_storage_order_do_not_change_geometry(self):
        self.assertTrue(self.measure(self.hanger[:, [2, 0, 1]])['pass'])


if __name__ == '__main__':
    unittest.main()
