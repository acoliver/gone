"""Focused physical contracts for the installed, baked seven-pod network."""
import json
import unittest

import numpy as np
import trimesh

from stasis_wiring_assemblies import OUT
from stasis_wiring_production import build_installation, measure_pods


class ProductionInstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = build_installation()

    def test_measured_gap_and_hidden_base_entries(self):
        metrics = self.assembly.metrics
        self.assertGreater(metrics['drop_pod_side_clearance_m'], .10)
        self.assertGreater(metrics['all_lid_sweep_vertical_clearance_m'], .04)
        self.assertEqual(len(metrics['terminal_centers_m']), 7)
        self.assertGreater(metrics['terminal_hidden_base_margin_m'], .02)
        self.assertGreater(measure_pods()['interpod_gap_m'], .5)

    def test_actual_contacts_and_support_spacing(self):
        for contact in self.assembly.contacts:
            self.assertTrue(contact['support_id'])
            for key, value in contact.items():
                if key.endswith('gap_m'):
                    self.assertLess(value, 2e-6, contact['id']+': '+key)
        for key, value in self.assembly.metrics.items():
            if key.endswith('support_pitch_m') or key.endswith('clip_pitch_m'):
                self.assertLessEqual(value, .8, key)
        for kind in ['power', 'data']:
            self.assertGreater(self.assembly.metrics[kind+'_complete_wall_conduit_maximum_support_pitch_m'],
                               self.assembly.metrics[kind+'_maximum_wall_clip_pitch_m'],
                               'include the real union-to-wall elbow arc, not just vertical clip pitch')

    def test_routes_are_measured_and_seven_terminal_pairs_connected(self):
        routes = {r['id']:r for r in self.assembly.routes}
        for route in routes.values():
            self.assertGreaterEqual(route['minimum_centerline_radius_m']+1e-4, route['required_centerline_radius_m'])
        for pod in range(1, 8):
            for kind in ['power', 'data']:
                self.assertIn(f'pod-{pod}-{kind}-1', routes)
        self.assertEqual(len(self.assembly.metrics['fault_connection_endpoints_m']), 4)
        for point in self.assembly.metrics['fault_connection_endpoints_m']:
            self.assertAlmostEqual(point[1], 2.82)
            self.assertLess(abs(point[2]+.6), .02)
        self.assertNotIn('steel_frame', self.assembly.parts)

    def test_floor_continuation_meets_each_of_the_eight_source_jackets(self):
        routes = {r['id']:r for r in self.assembly.routes}
        for kind,count in [('power',2),('data',6)]:
            for index in range(1,count+1):
                np.testing.assert_allclose(routes[f'{kind}-{index}']['end_m'],
                                           routes[f'{kind}-floor-entry-{index}']['start_m'],atol=1e-9)


    def test_exported_production_asset_bounds_and_no_context(self):
        path = OUT/'production-installation.glb'
        self.assertTrue(path.is_file())
        loaded = trimesh.load(path, force='scene')
        np.testing.assert_allclose(loaded.bounds, self.assembly.scene().bounds, atol=1e-6)
        self.assertLess(loaded.bounds[1, 1], 3.10)
        self.assertGreater(loaded.bounds[0, 1], -.85)
        self.assertGreater(self.assembly.metrics['service_envelope_clearance_m'], .002)


    def test_graph_requires_real_per_strand_junction_interfaces(self):
        import copy
        from stasis_wiring_installation_graph import graph
        valid = graph(self.assembly)
        self.assertEqual(len(valid['junction_interfaces']),224)
        damaged = copy.copy(self.assembly)
        damaged.metrics = dict(self.assembly.metrics)
        damaged.metrics['junction_links'] = [link for link in self.assembly.metrics['junction_links']
            if link['route']!='pod-1-power-1']
        with self.assertRaisesRegex(ValueError,'lacks physical strand interfaces'):
            graph(damaged)

    def test_source_has_two_real_output_ports_with_a_steel_partition(self):
        from stasis_wiring_export_checks import exported_group
        scene = trimesh.load(OUT/'production-installation.glb',force='scene')
        metal = exported_group(scene,'junction_metal')
        source = next(j for j in self.assembly.metrics['junctions'] if j['id']=='source-power-branch')
        center = np.array(source['center_m'])
        points = [center+[.0735,0,z] for z in [0,.078,.037]]
        np.testing.assert_array_equal(metal.contains(points),[False,False,True])

    def test_exported_all_buried_jackets_clear_pipe_and_box_triangles(self):
        from stasis_wiring_export_checks import verify_buried
        scene = trimesh.load(OUT/'production-installation.glb',force='scene')
        result = verify_buried(scene,self.assembly.routes,self.assembly.metrics)
        self.assertEqual(result['buried_routes'],88)
        self.assertEqual(result['connected_strand_junctions'],72)
        self.assertEqual(result['pipe_triangle_intersections'],0)
        self.assertEqual(result['box_triangle_intersections'],0)
        self.assertEqual(result['support_triangle_intersections'],0)

    def test_overhead_branches_clear_every_continuing_power_jacket(self):
        from stasis_wiring_export_checks import verify_overhead
        scene = trimesh.load(OUT/'production-installation.glb',force='scene')
        result = verify_overhead(scene,self.assembly.routes,self.assembly.metrics)
        self.assertGreater(result['minimum_surface_clearance_m'],0)
        self.assertTrue(all(n<=1 for n in result['review_point_closed_component_occupancy']))

    def test_export_probe_rejects_original_buried_wall_and_overhead_overlap(self):
        from stasis_wiring_export_checks import segment_hits, verify_overhead
        from stasis_wiring_assemblies import annulus
        shell,_ = annulus(np.array([[-5.15,-.55,-3.35],[-.25,-.55,-3.35]]),.027,.030)
        route = next(r for r in self.assembly.routes if r['id']=='power-floor-entry-1')
        self.assertGreater(segment_hits(shell,[np.array(route['centerline_m'])]),0)
        import copy
        routes = copy.deepcopy(self.assembly.routes)
        trunk = next(r for r in routes if r['id']=='power-1')
        branch = next(r for r in routes if r['id']=='fault-left-power-1')
        branch['centerline_m'] = trunk['centerline_m']
        with self.assertRaisesRegex(ValueError,'outside jacket overlap'):
            verify_overhead(trimesh.load(OUT/'production-installation.glb',force='scene'),routes,self.assembly.metrics)

if __name__ == '__main__':
    unittest.main()
