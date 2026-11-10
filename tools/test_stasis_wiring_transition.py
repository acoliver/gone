"""Issue 110: aligned source removes service loopbacks, not bend requirements."""
import json
import unittest

import numpy as np

from stasis_wiring_assemblies import OUT, transition

from stasis_wiring_clearance import segment_distance


class ContinuousPackingTests(unittest.TestCase):
    def test_crossing_segment_interiors_are_not_missed_by_sparse_samples(self):
        first = np.array([[-1., 0., 0.], [1., 0., 0.]])
        crossing = np.array([[0., -1., 0.], [0., 1., 0.]])
        self.assertAlmostEqual(segment_distance(first, crossing), 0.)
        self.assertAlmostEqual(segment_distance(first, crossing+[0., 0., .02]), .02)
        parallel = np.array([[-.5, .0064, 0.], [.5, .0064, 0.]])
        self.assertAlmostEqual(segment_distance(first, parallel), .0064)



class TransitionInstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = transition(json.loads((OUT/'sockets.json').read_text()))

    def test_endwall_mount_and_actual_socket_axes(self):
        metrics = self.assembly.metrics
        self.assertAlmostEqual(metrics['source_mount_back_plane_world_x_m'], -6)
        for route in self.assembly.routes:
            self.assertGreater(route['exit_axis_dot_world_plus_x'], .999)
            self.assertLess(route['socket_axis_radial_error_m'], .000001 if route['id'].startswith('power') else .006401)
            points = np.array(route['centerline_m'])
            # No reverse +X travel before the two purposeful wall/drop turns.
            self.assertGreaterEqual(np.diff(points[:, 0]).min(), -1e-8)
            self.assertAlmostEqual(points[-1, 1], -.1)

    def test_support_pitch_real_seals_and_floor_intersection(self):
        for kind in ['power', 'data']:
            metrics = self.assembly.metrics
            self.assertLessEqual(metrics[kind+'_maximum_exposed_support_pitch_m'], .6)
            self.assertLessEqual(metrics[kind+'_maximum_wall_clip_pitch_m'], .6)
            self.assertGreater(metrics[kind+'_entry_bushing_clearance_m'], 0)
            self.assertLess(metrics[kind+'_conduit_floor_intersection_y_range_m'][0], -.099)
            self.assertGreater(metrics[kind+'_conduit_floor_intersection_y_range_m'][1], .01)
        self.assertGreaterEqual(self.assembly.metrics['minimum_power_strand_surface_separation_m'], .001)
        self.assertGreaterEqual(self.assembly.metrics['minimum_power_data_surface_separation_m'], .01)
        self.assertGreaterEqual(self.assembly.metrics['maximum_authored_sag_m'], .002)
        self.assertLessEqual(self.assembly.metrics['maximum_authored_sag_m'], .005)
        for contact in self.assembly.contacts:
            self.assertIn('support_id', contact)
            for key, value in contact.items():
                if key.endswith('gap_m'):
                    self.assertLess(value, 1e-7, contact['id'])


if __name__ == '__main__':
    unittest.main()
