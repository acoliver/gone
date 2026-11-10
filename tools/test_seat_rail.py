"""Issue 110: the pickup is cut from the lower formed seat, not the upper carrier."""
import unittest
import numpy as np
from seat_rail import make_rail, rail_family, floor_pose, profile, OUT
import trimesh


class SeatRailTests(unittest.TestCase):
    def test_sheet_volume_has_open_channel_and_closed_metal(self):
        rail = make_rail()
        self.assertTrue(rail.is_watertight)
        self.assertTrue(rail.is_winding_consistent)
        np.testing.assert_allclose(rail.extents, [1.2, .018, .042], atol=1e-9)
        self.assertLess(rail.volume, 1.2*.018*.042*.45)
        # Hollow channel and punched slots must be empty space, not painted marks.
        np.testing.assert_array_equal(rail.contains([[.1,-.009,0],[.1,-.00125,0],
                                                    [.1,-.008,.01975],[-.351,-.008,.01975]]),
                                      [False,True,True,False])
        p = profile()
        top = p[np.isclose(p[:,0], 0)]
        self.assertAlmostEqual(np.ptp(top[:,1]), .036)

    def test_paired_cuts_share_exact_vertices_and_source_uv(self):
        family = rail_family()
        for label in ['left', 'right']:
            np.testing.assert_array_equal(family['cuts'][label]['retained'], family['cuts'][label]['fragment'])
        body = family['middle']
        full = family['full']
        for mesh in [family['left'], body, family['right']]:
            self.assertTrue(mesh.is_watertight)
            ids = mesh.metadata['source_vertex_ids']
            valid = ids >= 0
            np.testing.assert_array_equal(mesh.visual.uv[valid], full.visual.uv[ids[valid]])
            np.testing.assert_array_equal(mesh.vertices[valid], full.vertices[ids[valid]])
        self.assertGreater(body.extents[0]/body.extents[2], 23)

    def test_floor_pose_matches_cylinder_axis_and_proxy(self):
        middle = rail_family()['middle']
        pose = floor_pose(middle)
        moved = middle.copy()
        moved.apply_transform(pose)
        np.testing.assert_allclose(pose[:3,0], [np.sin(np.deg2rad(82)),0,np.cos(np.deg2rad(82))], atol=1e-12)
        self.assertAlmostEqual(moved.bounds[0,1],0,places=12)
        np.testing.assert_allclose(pose[[0,2],3],[-.6,-1.4],atol=1e-12)
        self.assertAlmostEqual(np.rad2deg(np.arctan2(pose[1,2],pose[1,1])),-115.)
        # The opening points sideways and up, resting on a folded edge.
        opening = pose[:3,:3] @ [0,-1,0]
        self.assertGreater(opening[1],.4)
        self.assertGreater(moved.bounds[1,1],.04)
        self.assertLess(moved.bounds[1,1],.05)
        # ShipLayout's bay frame maps local X to world -Z, matching the world-space picker.
        bay_basis = np.array([[0,0,1],[0,1,0],[-1,0,0]])
        world_vertices = moved.vertices @ bay_basis.T
        self.assertTrue(np.all(np.ptp(world_vertices,axis=0) <= [.22,.10,1.15]))
        restored = np.c_[moved.vertices,np.ones(len(moved.vertices))] @ np.linalg.inv(pose).T
        np.testing.assert_allclose(restored[:,:3],middle.vertices,atol=1e-12)

    def test_active_proof_failure_matches_production_without_healthy_seat_at_failure(self):
        from seat_rail_proof import CEILING_ORIGIN
        from stasis_wiring_assemblies import fault
        np.testing.assert_allclose(CEILING_ORIGIN,[-.6,2.988,-.6],atol=1e-12)
        assembly = fault()
        for mesh in assembly.parts['seat_retained']:
            self.assertAlmostEqual(mesh.bounds[:,2].mean(),CEILING_ORIGIN[2])
        for mesh in assembly.parts['seat_healthy']:
            center = mesh.bounds.mean(axis=0)
            self.assertGreater(np.linalg.norm(center[[0,2]]-CEILING_ORIGIN[[0,2]]),.1)

    def test_proof_has_one_intact_upper_and_no_replaced_or_duplicate_ledgers(self):
        from seat_rail_context_checks import frame_metrics
        metrics=frame_metrics()
        self.assertEqual(metrics['frame_components'],28)
        self.assertEqual(metrics['duplicated_frame_components'],0)
        self.assertEqual(metrics['replaced_flat_cross_ledger_count'],0)
        self.assertEqual(metrics['intact_upper_carrier_at_failure_count'],1)
        self.assertEqual(metrics['long_flat_ledger_count'],12)

    def test_baked_floor_mesh_matches_current_pose_without_changing_uv(self):
        from scipy.spatial import cKDTree
        source=rail_family()['middle']
        expected=trimesh.transform_points(source.vertices,floor_pose(source))
        scene=trimesh.load(OUT.parent/'fault-frame-pair.glb',force='scene')
        actual=scene.geometry['fallen_fragment']
        distance,ids=cKDTree(expected).query(actual.vertices)
        self.assertLess(distance.max(),1e-7)
        np.testing.assert_allclose(actual.visual.uv,source.visual.uv[ids],atol=1e-6)
        self.assertAlmostEqual(actual.bounds[0,1],0.,places=7)


if __name__ == '__main__':
    unittest.main()
