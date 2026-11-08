"""Ordered sofa contacts must never depend on a mixed-pose comparison bake."""
import unittest

from sofa_decay_policy import ORDER, cushion_plan


class OrderedDecayTests(unittest.TestCase):
    def test_seats_precede_backs_with_unique_seeds(self):
        self.assertTrue(all(n.startswith('Seat') for n in ORDER[:3]))
        self.assertTrue(all(n.startswith('Back') for n in ORDER[3:]))
        self.assertEqual(len({cushion_plan(n)['seed'] for n in ORDER}), 6)

    def test_only_final_predecessors_are_neighbour_colliders(self):
        for index, name in enumerate(ORDER):
            self.assertEqual(cushion_plan(name)['settled_contacts'], list(ORDER[:index]))
            self.assertNotIn(name, cushion_plan(name)['settled_contacts'])

    def test_centre_and_side_seats_have_different_residue_and_rest(self):
        plans = [cushion_plan(n) for n in ORDER[:3]]
        self.assertEqual(len({p['residue_height_scale'] for p in plans}), 3)
        self.assertTrue(all(p['pins'] == 0 for p in plans))

    def test_unknown_part_fails(self):
        with self.assertRaises(ValueError):
            cushion_plan('Unknown')


if __name__ == '__main__':
    unittest.main()
