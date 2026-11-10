"""The throw must retain a connected trail from the arm crease to the floor."""
import unittest

import trimesh

from sofa_decay_measure import throw_connectivity


def strip(y=-.1):
    return trimesh.Trimesh(vertices=[(1.01, y, .80), (1.11, y, .80),
                                    (1.11, y, .004), (1.01, y, .004)],
                           faces=[(0, 1, 2), (0, 2, 3)], process=False)


class ThrowContinuity(unittest.TestCase):
    def test_one_sheet_trails_from_arm_to_floor(self):
        value = throw_connectivity(strip())
        self.assertEqual(value['components'], 1)
        self.assertEqual(value['arm_to_floor_components'], 1)
        self.assertTrue(value['continuous_arm_to_floor'])

    def test_floor_scrap_does_not_count_as_a_trail(self):
        mesh = trimesh.creation.box((.25, .3, .005))
        mesh.apply_translation((1.1, -.1, .006))
        self.assertFalse(throw_connectivity(mesh)['continuous_arm_to_floor'])

    def test_only_one_detached_remnant_is_allowed(self):
        remnant = trimesh.creation.box((.01, .01, .001))
        remnant.apply_translation((1.8, -.1, .006))
        self.assertTrue(throw_connectivity(trimesh.util.concatenate([strip(), remnant]))['continuous_arm_to_floor'])
        second = remnant.copy()
        second.apply_translation((.1, 0, 0))
        self.assertFalse(throw_connectivity(trimesh.util.concatenate([strip(), remnant, second]))['continuous_arm_to_floor'])

    def test_two_independent_trails_do_not_count_as_one_piece(self):
        self.assertFalse(throw_connectivity(trimesh.util.concatenate([strip(), strip(.1)]))['continuous_arm_to_floor'])


if __name__ == '__main__':
    unittest.main()
