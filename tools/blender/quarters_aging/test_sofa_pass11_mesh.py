"""Blender controls for broad physical gashes and area-preserving back lean."""
from pathlib import Path
import sys
import unittest
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fabric_mesh import new_object, material
from sofa_pass11_mesh import cut_gash, gash_field, lean_back, seat_bowl, surface_area
from sofa_pass9_finish import points


class GashTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def grid(self):
        n = 21
        p = [(x*.02-.2, y*.02-.2, 0.) for y in range(n) for x in range(n)]
        f = [(y*n+x, y*n+x+1, (y+1)*n+x+1, (y+1)*n+x) for y in range(n-1) for x in range(n-1)]
        return new_object('Control', p, f, material('Cloth', (.05, .05, .05)))

    def test_broad_gash_removes_real_faces_and_tags_physical_lips(self):
        obj = self.grid()
        spec = dict(centre=[0, 0, 0], tangent=[1, 0, 0], across=[0, 1, 0], half_length=.1, half_width=.035, seed=9601)
        before = surface_area(obj)
        report = cut_gash(obj, spec)
        self.assertLess(surface_area(obj), before-.003)
        self.assertGreater(report['lip_edges'], 30)
        self.assertIn('Broad gash', obj.vertex_groups)
        self.assertTrue(np.isfinite(report['opening_span_m']))
        self.assertTrue(np.isfinite(report['opening_width_m']))
        self.assertGreater(report['opening_span_m'], .18)
        self.assertGreater(report['opening_width_m'], .035)
        self.assertTrue(np.isfinite(points(obj)).all())

    def test_back_lean_is_rigid_without_area_loss_or_stretch(self):
        obj = self.grid()
        before = surface_area(obj)
        p = points(obj)
        report = lean_back(obj, 25, floor=-.3)
        self.assertAlmostEqual(surface_area(obj)/before, 1., places=6)
        q = points(obj)
        np.testing.assert_allclose(np.linalg.norm(q-q[0], axis=1), np.linalg.norm(p-p[0], axis=1), atol=1e-6)
        self.assertAlmostEqual(report['area_ratio'], 1., places=6)

    def test_seat_bowl_keeps_its_middle_lower_than_both_sides(self):
        p = np.array([[-.29, -.08, .42], [0, -.08, .42], [.29, -.08, .42]])
        q = seat_bowl(p, centre=0., amount=.025)
        self.assertLess(q[1, 2], q[0, 2]-.015)
        self.assertLess(q[1, 2], q[2, 2]-.015)
        self.assertAlmostEqual(q[1, 2], p[1, 2])

    def test_gash_cuts_parallel_plies_consistently(self):
        spec = dict(centre=[0, 0, 0], tangent=[1, 0, 0], across=[0, 1, 0], half_length=.1, half_width=.035, seed=9601)
        p = np.array([[0, 0, 0], [.08, .04, 0], [.12, 0, 0]])
        np.testing.assert_allclose(gash_field(p, spec), gash_field(p+[0, 0, .03], spec))
        self.assertLess(gash_field(p, spec)[0], 0.)
        self.assertGreater(gash_field(p, spec)[2], 0.)

    def test_back_cut_does_not_perforate_hidden_rear_folds(self):
        spec = dict(centre=[0, 0, 0], tangent=[0, 0, 1], across=[1, 0, 0],
                    half_length=.07, half_width=.035, seed=9912, depth_max=.028)
        result = gash_field(np.array([[0, 0, 0], [0, .04, 0]]), spec)
        self.assertLess(result[0], 0.)
        self.assertGreater(result[1], 0.)

    def test_edge_fraying_does_not_add_interior_wear_holes(self):
        from sofa_pass11_material import frayed_coverage
        p = np.array([[x, 0., 0.] for x in np.linspace(-.2, .2, 101)])
        result = frayed_coverage(p, np.full(len(p), .010), p, 9801)
        self.assertTrue(result.all())
        edge = frayed_coverage(p, np.full(len(p), .0017), p, 9801)
        self.assertTrue(edge.any())
        self.assertFalse(edge.all())


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GashTests))
    if not result.wasSuccessful():
        raise RuntimeError('Pass-11 geometry controls failed')
