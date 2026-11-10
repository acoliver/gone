import copy
import unittest

from collision_policy import sofa_contacts


class SofaContactPolicy(unittest.TestCase):
    def setUp(self):
        self.baseline = {'self': {n: {'count': 522 if n == 'Frame' else 0}
                                  for n in ['Frame', 'Feet', 'Rivets']},
                         'pairs': {'Frame/Rivets': {'count': 272}}}

    def test_only_exact_rigid_baseline_is_accepted(self):
        result = sofa_contacts(self.baseline, self.baseline)
        self.assertTrue(result['pass'])
        self.assertEqual(result['changed_intersections'], 0)
        changed = copy.deepcopy(self.baseline)
        changed['self']['Frame']['count'] -= 1
        self.assertFalse(sofa_contacts(changed, self.baseline)['pass'])

    def test_changed_self_rigid_and_new_part_contacts_fail(self):
        for section, name in [('self', 'SeatCushion_C'), ('pairs', 'Frame/SeatCushion_C'),
                              ('pairs', 'Feet/Fringe'), ('pairs', 'Powder/Crumbs')]:
            changed = copy.deepcopy(self.baseline)
            changed[section][name] = {'count': 1}
            result = sofa_contacts(changed, self.baseline)
            self.assertFalse(result['pass'])
            self.assertEqual(result['changed_intersections'], 1)

    def test_missing_rigid_part_fails_visibly(self):
        changed = copy.deepcopy(self.baseline)
        del changed['self']['Rivets']
        with self.assertRaises(KeyError):
            sofa_contacts(changed, self.baseline)


if __name__ == '__main__':
    unittest.main()
