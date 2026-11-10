import unittest

import numpy as np
import trimesh

from stasis_wiring_assemblies import (Assembly, transition, fault, OUT,
                                      physical_route_graph, validate_physical_graph)
from seat_rail import rail_family
import json


class AssemblyTests(unittest.TestCase):
    def test_source_bores_fit_each_distinct_jacket_and_exit_forward(self):
        assembly = transition(json.loads((OUT/'sockets.json').read_text()))
        self.assertEqual(len(assembly.routes), 8)
        graph = physical_route_graph(assembly.routes)
        self.assertEqual(len(graph['source_feed_pairs']),8)
        graph['edges'].pop()
        with self.assertRaisesRegex(ValueError,'disconnected physical feed'):
            validate_physical_graph(graph,assembly.routes)
        for route in assembly.routes:
            self.assertGreater(route['socket_radial_clearance_m'], 0)
            self.assertGreater(route['minimum_conduit_inscribed_bore_clearance_m'], 0)
            # Issue 110: the measured local +Z socket now faces world +X.
            self.assertGreater(route['exit_axis_dot_world_plus_x'], .999)
            self.assertGreaterEqual(route['minimum_centerline_radius_m'], route['required_centerline_radius_m']-.0001)
            self.assertGreaterEqual(route['minimum_surface_longitudinal_radius_m'], route['required_centerline_radius_m']-route['jacket_od_m']/2-.0004)
        self.assertGreaterEqual(assembly.metrics['data_minimum_strand_surface_separation_m'], .00035)
        self.assertLess(assembly.metrics['data_envelope_at_bore_m'], .020)
        for contact in assembly.contacts:
            for key,value in contact.items():
                if key.endswith('gap_m'): self.assertLess(value, 1e-7, contact['id'])

    def test_invalid_radius_and_actual_missing_contact_fail(self):
        assembly = Assembly('negative-control')
        t = np.linspace(0, np.pi/2, 100)
        tight = np.column_stack([.03*np.cos(t), np.zeros(100), .03*np.sin(t)])
        with self.assertRaisesRegex(ValueError, 'bend radius'):
            assembly.route('too-tight', tight, .003, .048)
        path = np.column_stack([np.linspace(0,1,101),np.zeros(101),np.zeros(101)])
        mesh,_ = assembly.route('straight',path,.012,.144)
        displaced = mesh.copy()
        displaced.apply_translation([0,0,.01])
        with self.assertRaisesRegex(ValueError, 'clamp misses'):
            assembly.clamp('detached',path,.012,50,displaced,rail=False)

    def test_shared_fracture_annuli_and_exact_inverse_fallen_transform(self):
        # Issue 110 user correction: fracture the lower thin-sheet seat;
        # the separate 55 mm upper carrier must remain intact.
        member = rail_family()['middle']
        self.assertTrue(member.is_watertight)
        self.assertTrue(member.is_winding_consistent)
        self.assertTrue(np.all(abs(member.bounds[:,0]-[-.5,.5])<.0021))
        np.testing.assert_allclose(member.extents[1:],[.018,.042])
        assembly = fault()
        fracture = assembly.metrics['fracture']
        self.assertEqual(fracture['retained_end_sha256'],fracture['fragment_original_end_sha256'])
        self.assertLess(fracture['inverse_transformed_mesh_max_error_m'],1e-12)
        self.assertAlmostEqual(fracture['fallen_mesh_bounds_m'][0][1],0.,places=12)
        self.assertFalse(assembly.metrics['fragment_has_cable_attachment'])

    def test_one_fault_has_short_supported_power_and_three_local_copper_tips(self):
        assembly = fault()
        self.assertEqual(assembly.metrics['opening_cell'],[4,4])
        self.assertEqual(len(assembly.metrics['power_core_tips_m']),3)
        self.assertTrue(all(tip[1]>2.1 for tip in assembly.metrics['power_core_tips_m']))
        for route in assembly.routes[:2]:
            self.assertLessEqual(route['start_m'][1]-route['end_m'][1],.5)
            self.assertGreater(route['actual_mesh_bounds_m'][0][1],2.1)
            self.assertLessEqual(route['start_m'][1]-route['actual_mesh_bounds_m'][0][1],.5)
        self.assertEqual(len(assembly.routes[2:]),6)
        self.assertEqual(assembly.metrics['power_core_exposed_length_m'],.004)
        for contact in assembly.contacts:
            for key,value in contact.items():
                if key.endswith('gap_m'): self.assertLess(value,1e-7,contact['id'])


if __name__ == '__main__':
    unittest.main()
