"""Opening-disc regression on triangulated, perpendicular round-wire links."""
import unittest

import numpy as np

from medal_interlink import reciprocal_interlink


def ring_mesh():
    vertices, faces = [], []
    for i in range(48):
        angle = 2 * np.pi * i / 48
        for j in range(12):
            wire = 2 * np.pi * j / 12
            radius = .003 + .00045 * np.cos(wire)
            vertices.append([.00045 * np.sin(wire), radius * np.cos(angle), .020 + radius * np.sin(angle)])
    for i in range(48):
        for j in range(12):
            a, b = i * 12 + j, ((i + 1) % 48) * 12 + j
            c, d = ((i + 1) % 48) * 12 + (j + 1) % 12, i * 12 + (j + 1) % 12
            faces.extend([(a, b, c), (a, c, d)])
    return np.asarray(vertices), np.asarray(faces)


class InterlinkTest(unittest.TestCase):
    def setUp(self):
        self.vertices, self.faces = ring_mesh()
        self.loop = dict(center_m=[.0003, .0001, .023], up=[0., 0., 1.], normal=[0., 1., 0.],
                         radius_m=.003, wire_radius_m=.00045, major_segments=40)

    def test_perpendicular_links_cross_both_opening_discs(self):
        result = reciprocal_interlink(self.vertices, self.faces, .000013, self.loop)
        self.assertTrue(result['loop_through_ring_disc'])
        self.assertTrue(result['ring_through_loop_disc'])
        self.assertEqual(result['perpendicular_plane_normal_dot'], 0.)

    def test_adjacent_unlinked_loop_is_rejected(self):
        self.loop['center_m'][0] += .010
        with self.assertRaises(AssertionError):
            reciprocal_interlink(self.vertices, self.faces, .000013, self.loop)

    def test_loop_above_the_opening_is_rejected(self):
        self.loop['center_m'][2] += .010
        with self.assertRaises(AssertionError):
            reciprocal_interlink(self.vertices, self.faces, .000013, self.loop)

    def test_first_disc_alone_does_not_establish_interlink(self):
        self.loop['wire_radius_m'] = .0028
        with self.assertRaisesRegex(AssertionError, 'Ring centreline must cross the loop opening'):
            reciprocal_interlink(self.vertices, self.faces, .000013, self.loop)

    def test_nonperpendicular_planes_are_rejected(self):
        self.loop['normal'] = [1., 0., 0.]
        with self.assertRaises(AssertionError):
            reciprocal_interlink(self.vertices, self.faces, .000013, self.loop)


if __name__ == '__main__':
    unittest.main()
