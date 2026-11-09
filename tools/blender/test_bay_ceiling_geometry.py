"""Numerical regressions for the source-derived ceiling fit, without Blender."""
import json
from pathlib import Path
import unittest

import numpy as np

from bay_ceiling_geometry import (
    FittedGuides, RIM_DEPTH, RIM_FRACTIONS, RIM_HEIGHTS, assert_simple,
    constraint_loop, contains, distance_to_loop, signed_area,
)

ROOT = Path(__file__).resolve().parents[2]


class BayCeilingGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit = FittedGuides(json.loads((ROOT / 'art-source/bay-ceiling/source-guide.json').read_text()))

    def test_source_outline_is_centered_and_target_sized(self):
        np.testing.assert_allclose(self.fit.outer.min(axis=0), [-.59, -.29], atol=1e-8)
        np.testing.assert_allclose(self.fit.outer.max(axis=0), [.59, .29], atol=1e-8)
        for residual in self.fit.record['guide_residual_to_fitted_polyline'].values():
            self.assertLess(residual['rms_m'], .002)
            self.assertLess(residual['max_m'], .008)
        self.assertTrue(contains(self.fit.inner, self.fit.outer).all())

    def test_mechanical_flange_has_two_mm_reveal_and_eight_mm_bearing(self):
        # The mounting edge is formed to the shared grid; the inner source rim stays fitted.
        from bay_ceiling_geometry import radial
        for axis, halfspan, pitch in ((0, .59, 1.2), (1, .29, .6)):
            other = 1 - axis
            for sign in (-1, 1):
                for t in np.linspace(-.85, .85, 31):
                    point = np.zeros(2)
                    point[axis] = sign * halfspan
                    point[other] = t * (.29 if axis == 0 else .59)
                    edge = radial(self.fit.outer, np.array([np.arctan2(point[1], point[0])]))[0]
                    self.assertAlmostEqual(abs(edge[axis]), halfspan, places=7)
                    self.assertAlmostEqual(pitch / 2 - .008 - abs(edge[axis]), .002)
                    self.assertAlmostEqual(abs(edge[axis]) - (pitch / 2 - .018), .008)
                    contact = edge.copy()
                    contact[axis] -= sign * .004
                    self.assertTrue(contains(contact, self.fit.profile_rings('intact')[0])[0])
                    self.assertFalse(contains(contact, self.fit.profile_rings('intact')[2])[0])
                    self.assertAlmostEqual(self.fit.displacement(contact, 'sag')[0], 0.)

    def test_central_span_adjustment_preserves_end_vector_lengths(self):
        for side in (-1, 1):
            source_points = self.fit.center + np.array([[side*.4, 0.], [side*.45, .05]]) / self.fit.scale
            mapped = self.fit.fit_plan(source_points)
            np.testing.assert_allclose(mapped[1] - mapped[0], [side*.05, .05], atol=1e-10)

    def test_capsules_have_positive_ligaments(self):
        self.assertEqual(len(self.fit.slots), 28)
        self.assertTrue(all(len(slot) == 16 for slot in self.fit.slots))
        self.assertGreaterEqual(self.fit.slot_gap, .008)
        self.assertGreaterEqual(self.fit.slot_rim_gap, .008)

    def test_collinear_removal_preserves_the_contour(self):
        simplified = constraint_loop(self.fit.outer, self.fit.contact_indices)
        # Straight mounting edges collapse to their endpoints; rounded corners remain.
        self.assertGreaterEqual(len(simplified), 36)
        self.assertLess(len(simplified), len(self.fit.outer))
        self.assertLess(distance_to_loop(self.fit.outer, simplified).max(), 3e-7)
        assert_simple(simplified)

    def test_displacements_pin_entire_outer_contact_ring(self):
        for kind in ('subtlewarp', 'sag'):
            np.testing.assert_allclose(self.fit.displacement(self.fit.outer, kind), 0, atol=1e-12)
        self.assertAlmostEqual(self.fit.displacement(np.array([[0., 0.]]), 'sag')[0], -.036)
        twist = self.fit.displacement(np.array([[-.20, 0.], [.20, 0.]]), 'subtlewarp')
        self.assertLess(twist[0], 0)
        self.assertGreater(twist[1], 0)

    def test_raised_profile_keeps_measured_plan_contours(self):
        self.assertEqual(RIM_DEPTH, .018)
        self.assertEqual(len(RIM_FRACTIONS), 5)
        self.assertEqual(RIM_HEIGHTS[0], 0.)
        self.assertEqual(RIM_HEIGHTS[-1], -RIM_DEPTH)
        rings = self.fit.profile_rings('intact')
        np.testing.assert_array_equal(rings[0], self.fit.outer)
        np.testing.assert_array_equal(rings[-1], self.fit.inner)
        for outer, inner in zip(rings, rings[1:]):
            assert_simple(outer)
            self.assertTrue(contains(inner, outer).all())

    def test_notches_remove_contiguous_regions_without_crossing_slots(self):
        directions = np.array([np.pi / 2, np.pi, 0.])
        broken_weights = self.fit.damage_weight(directions, 'brokenedge')
        self.assertGreater(broken_weights[0], .85)
        self.assertLess(broken_weights[1], .01)
        self.assertLess(broken_weights[2], .01)
        for kind in ('torncorner', 'brokenedge'):
            outer = self.fit.damaged_outer(kind)
            assert_simple(outer)
            self.assertTrue(contains(self.fit.inner, outer).all())
            changed = np.linalg.norm(outer - self.fit.outer, axis=1) > 1e-9
            self.assertEqual(np.count_nonzero(changed != np.roll(changed, 1)), 2)
            minimum_depth = .040 if kind == 'torncorner' else .030
            self.assertGreater(np.linalg.norm(outer - self.fit.outer, axis=1).max(), minimum_depth)
            self.assertGreater(signed_area(self.fit.outer) - signed_area(outer), .004)
            arc = np.linalg.norm(np.roll(self.fit.outer, -1, axis=0) - self.fit.outer, axis=1)
            self.assertGreater(arc[changed].sum(), .22)
            bend = self.fit.displacement(outer, kind)
            self.assertLess(bend.min(), -.024)
            self.assertGreater(np.ptp(bend[changed]), .020)
            for a, b in zip(self.fit.profile_rings(kind), self.fit.profile_rings(kind)[1:]):
                assert_simple(a)
                self.assertTrue(contains(b, a).all())
            self.assertTrue(all(contains(slot, outer).all() for slot in self.fit.slots))
        corner = self.fit.contact_indices[-1]
        self.assertGreater(np.linalg.norm(self.fit.damaged_outer('torncorner')[corner] - self.fit.outer[corner]), .04)

    def test_four_flange_mounts_stay_fixed_outside_damage(self):
        reference = self.fit.attachment_points('intact')
        for kind in ('intact', 'subtlewarp', 'sag', 'torncorner', 'brokenedge'):
            points = self.fit.attachment_points(kind)
            self.assertEqual(points.shape, (4, 2))
            np.testing.assert_allclose(self.fit.displacement(points, kind), 0., atol=1e-12)
            self.assertTrue(contains(points, self.fit.damaged_outer(kind)).all())
            self.assertGreater(distance_to_loop(points, self.fit.damaged_outer(kind)).min(), .006)
            self.assertTrue(np.all(np.sign(points) == np.sign(reference)))
        self.assertGreater(np.linalg.norm(self.fit.attachment_points('torncorner')[-1] - reference[-1]), .1)


if __name__ == '__main__':
    unittest.main()
