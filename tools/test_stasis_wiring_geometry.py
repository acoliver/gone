import unittest
import numpy as np
from stasis_wiring_geometry import DATA, POWER, fillet_polyline, support_stations, sweep_strands


class GeometryTests(unittest.TestCase):
    def test_fillets_respect_radius_and_route_arclength(self):
        raw=np.array([[0.,0.,0.],[1.,0.,0.],[1.,0.,1.]])
        path=fillet_polyline(raw,POWER.bend_radius,40)
        self.assertLess(np.linalg.norm(np.diff(path,axis=0),axis=1).sum(),2.0)
        np.testing.assert_allclose(path[[0,-1]],raw[[0,-1]])
        for a,b,c in zip(path[1:-1],path[2:],path[3:]):
            ab=np.linalg.norm(a-b); bc=np.linalg.norm(b-c); ca=np.linalg.norm(c-a)
            area=np.linalg.norm(np.cross(b-a,c-a))/2
            if area > 1e-10:
                self.assertGreaterEqual(ab*bc*ca/(4*area),POWER.bend_radius-0.01)

    def test_short_corner_segments_and_reversals_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError,"too short"):
            fillet_polyline([[0,0,0],[.1,0,0],[.1,0,.1]],.144)
        with self.assertRaisesRegex(ValueError,"reversal"):
            fillet_polyline([[0,0,0],[1,0,0],[0,0,0]],.144)

    def test_strands_are_independent_watertight_outward_meshes(self):
        for cable in [POWER,DATA]:
            meshes=sweep_strands([[0,0,0],[1,0,0],[1,0,1]],cable)
            self.assertEqual(len(meshes),cable.strand_count)
            for mesh in meshes:
                self.assertTrue(mesh.is_watertight)
                self.assertTrue(mesh.is_winding_consistent)
                self.assertGreater(mesh.volume,0)
                self.assertTrue(np.isfinite(mesh.vertex_normals).all())
                self.assertGreater(np.ptp(mesh.bounds,axis=0).max(),0)
            if len(meshes)>1:
                self.assertGreater(np.linalg.norm(meshes[0].centroid-meshes[1].centroid),cable.diameter)

    def test_support_station_spacing_is_bounded_and_includes_contacts(self):
        stations=support_stations([[0,0,0],[1.7,0,0]],.4)
        self.assertLessEqual(np.linalg.norm(np.diff(stations,axis=0),axis=1).max(),.4000001)
        np.testing.assert_allclose(stations[[0,-1]],[[0,0,0],[1.7,0,0]])

if __name__ == '__main__':
    unittest.main()
