"""Controls for exported-bedding acceptance measurements."""
import unittest
import numpy as np
import trimesh
from verify import crossings, support_gap, volume_gate, axes_gate
from fit_contacts import headboard_shift


class GateTests(unittest.TestCase):
    def test_crossing_triangles_are_detected(self):
        a = trimesh.Trimesh(vertices=[[-1, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[0, 1, 2]], process=False)
        b = trimesh.Trimesh(vertices=[[0, .25, -1], [0, .25, 1], [0, -.25, 0]], faces=[[0, 1, 2]], process=False)
        self.assertEqual(crossings(a, b), 1)
        b.apply_translation([4, 0, 0])
        self.assertEqual(crossings(a, b), 0)

    def test_gap_is_measured_in_exported_y_up(self):
        support = trimesh.creation.box(extents=[2, .1, 2])
        part = trimesh.creation.box(extents=[1, .2, 1])
        part.apply_translation([0, .151, 0])
        self.assertAlmostEqual(support_gap(part, support), .001)
        part.apply_translation([0, .01, 0])
        self.assertGreater(support_gap(part, support), .003)

    def test_contact_interior_crest_is_not_missed_between_part_vertices(self):
        support = trimesh.Trimesh(vertices=[[-1, 0, -1], [1, 0, -1], [1, 0, 1], [-1, 0, 1], [0, .01, 0]],
                                  faces=[[0, 4, 1], [1, 4, 2], [2, 4, 3], [3, 4, 0]], process=False)
        part = trimesh.Trimesh(vertices=[[-.8, .009, -.8], [.8, .009, -.8], [0, .009, .8]],
                               faces=[[0, 1, 2]], process=False)
        self.assertAlmostEqual(support_gap(part, support), -.001)
        part.apply_translation([0, .002, 0])
        self.assertAlmostEqual(support_gap(part, support), .001)

    def test_pillow_back_shift_stops_at_headboard_in_exported_space(self):
        headboard = trimesh.creation.box(extents=[2, 1, .1])
        headboard.apply_translation([0, .6, -1.05])
        pillow = trimesh.creation.box(extents=[.6, .18, .4])
        pillow.apply_translation([0, .8, -.7])
        pillow.apply_translation([0, 0, -headboard_shift(pillow, headboard)])
        self.assertAlmostEqual(pillow.bounds[0, 2] - headboard.bounds[1, 2], .001)

    def test_volume_band_rejects_fluffy_or_vanished_mattress(self):
        for value in (.25, .32, .40):
            self.assertTrue(volume_gate(value))
        for value in (.249, .401, 1., 0., float('nan')):
            self.assertFalse(volume_gate(value))

    def test_axis_check_rejects_sideways_and_reversed_bed(self):
        mattress = trimesh.creation.box(extents=[1.4, .22, 1.96])
        mattress.apply_translation([0, .611, .025])
        pillows = trimesh.creation.box(extents=[1.3, .15, .43])
        pillows.apply_translation([0, .8, -.7])
        self.assertTrue(axes_gate(mattress, pillows))
        sideways = mattress.copy()
        sideways.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        self.assertFalse(axes_gate(sideways, pillows))
        pillows.apply_translation([0, 0, 1.4])
        self.assertFalse(axes_gate(mattress, pillows))


if __name__ == '__main__':
    unittest.main()
