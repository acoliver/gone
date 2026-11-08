"""Numerical controls distinguish crisp artificial holes from varied tears."""
import json
import unittest

import numpy as np

from seat_image_gates import evaluate, normal_jumps, opening_metrics, visible_dihedrals


class SeatImageGates(unittest.TestCase):
    def test_visible_dihedrals_do_not_count_occluded_face_pairs(self):
        vertices = np.array([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                             (2, 0, 0), (3, 0, 0), (3, 1, 0), (2, 0, 1)])
        faces = np.array([(0, 1, 2), (0, 2, 3), (4, 5, 6), (5, 4, 7)])
        identifiers = np.arange(1, 5)
        visible = np.zeros((40, 40, 3), dtype=np.uint8)
        visible[:, :20, 0] = 1
        visible[:, 20:, 0] = 2
        result = visible_dihedrals(vertices, faces, identifiers, [visible])
        self.assertEqual(result['fraction'], 0.)
        self.assertEqual(result['all_sheet_fraction'], .5)
        opposite = visible.copy()
        opposite[:, :, 0] += 2
        self.assertFalse(visible_dihedrals(vertices, faces, identifiers, [visible, opposite])['pass'])

    def test_flat_normal_pass_has_no_interior_jumps(self):
        cloth = np.ones((80, 80), dtype=bool)
        normal = np.full((80, 80, 3), [128, 128, 255], dtype=np.uint8)
        result = normal_jumps(normal, cloth)
        self.assertEqual(result['fraction'], 0)
        self.assertTrue(result['pass'])
        json.dumps(result)

    def test_abrupt_shading_jumps_fail(self):
        normal = np.full((80, 80, 3), [128, 128, 255], dtype=np.uint8)
        normal[:, ::2] = [255, 128, 255]
        self.assertFalse(normal_jumps(normal, np.ones((80, 80), dtype=bool))['pass'])

    def test_constant_width_rectangle_fails_straight_run_and_width_controls(self):
        cloth = np.ones((300, 300), dtype=bool)
        cloth[100:120, 30:270] = False
        result = opening_metrics(cloth)[0]
        self.assertGreater(result['longest_straight_run_px'], 12)
        self.assertLess(result['width_cv'], .35)

    def test_missing_visible_openings_cannot_pass_tear_gates(self):
        normal = np.full((80, 80, 3), [128, 128, 255], dtype=np.uint8)
        result = evaluate(np.ones((80, 80), dtype=int), normal)
        for gate in ['G3', 'G4', 'G6']:
            self.assertFalse(result[gate]['pass'])


if __name__ == '__main__':
    unittest.main()
