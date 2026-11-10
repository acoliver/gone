"""Production fault contracts, including continuous clearance and exact tips."""
import unittest

import numpy as np

from stasis_wiring_fault import add_fault, audit_fault, verify_exported_tips
from stasis_wiring_production import build_installation
from stasis_wiring_installation_graph import graph


class ProductionFaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = build_installation()
        cls.fault = cls.assembly.metrics['fault']

    def test_three_physical_tips_and_one_closed_jacket(self):
        self.assertEqual([r['id'] for r in self.fault['leads']],
                         ['released-left-1', 'released-left-2', 'released-right-1'])
        self.assertEqual(self.fault['sealed_connection'], 'fault-right-power-2')
        self.assertEqual(len(self.fault['tips']), 3)
        for lead, tip in zip(self.fault['leads'], self.fault['tips']):
            self.assertEqual(tip['class'], 'power')
            self.assertEqual(tip['lead'], lead['id'])
            self.assertAlmostEqual(np.linalg.norm(np.subtract(tip['end_m'], tip['start_m'])), .004)
            self.assertGreaterEqual(lead['minimum_centerline_radius_m'], .048-1e-4)
            self.assertLess(lead['retained_clamp_contact_gap_m'], 1e-7)
            self.assertLess(lead['jacket_to_core_axis_gap_m'], 1e-9)

    def test_fault_clears_all_lids_services_and_camera_capsules(self):
        for key in ['full_lid_arc_clearance_lower_bound_m', 'service_clearance_lower_bound_m',
                    'standing_capsule_vertical_gap_m', 'get_up_camera_capsule_vertical_gap_m']:
            self.assertGreater(self.fault[key], .003, key)
        self.assertEqual(self.fault['lid_count'], 7)
        self.assertGreater(self.fault['lid_arc_intervals_per_pod'], 100)

    def test_semantic_fault_ends_are_reachable_and_specific(self):
        data = graph(self.assembly)
        reached = {'enclosure'}
        for _ in data['nodes']:
            reached.update(e['to'] for e in data['edges'] if e['from'] in reached)
        for tip in self.fault['tips']:
            self.assertIn(tip['id'], reached)
        self.assertIn('fault_right_2_sealed', reached)
        self.assertEqual(data['fault']['power_tip_positions'], [t['end_m'] for t in self.fault['tips']])
        self.assertTrue(data['fault']['released_cores_and_sparks_installed'])

    def test_exported_actual_copper_tips(self):
        import trimesh
        from stasis_wiring_assemblies import OUT
        exported = trimesh.load(OUT/'production-installation.glb',force='scene')
        self.assertEqual(verify_exported_tips(exported,self.fault)['exposed_copper_solids'],3)

    def test_duplicate_installation_fails(self):
        with self.assertRaisesRegex(ValueError, 'already installed'):
            add_fault(self.assembly)

    def test_bad_tip_length_is_rejected(self):
        import copy
        broken = copy.deepcopy(self.fault)
        broken['tips'][0]['end_m'][1] -= .01
        with self.assertRaisesRegex(ValueError, '4 mm'):
            audit_fault(self.assembly, broken)


if __name__ == '__main__':
    unittest.main()
