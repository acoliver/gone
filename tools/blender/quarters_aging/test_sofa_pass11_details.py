"""Controls for fibre density and economical, non-icosahedral crumbs."""
from pathlib import Path
import sys
import unittest

import bmesh
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_pass11_fringe import stations, bundle_atlas
from sofa_pass11_fragments import compact


class DetailTests(unittest.TestCase):
    def test_fibre_station_count_does_not_depend_on_edge_tessellation(self):
        coarse = np.array([[0., 0, 0], [1., 0, 0]])
        fine = np.c_[np.linspace(0, 1, 1001), np.zeros((1001, 2))]
        a, ta, sa = stations(coarse, .012)
        b, tb, sb = stations(fine, .012)
        self.assertEqual(len(a), len(b))
        pa = coarse[a]+(coarse[a+1]-coarse[a])*ta[:, None]
        pb = fine[b]+(fine[b+1]-fine[b])*tb[:, None]
        np.testing.assert_allclose(pa, pb, atol=1e-10)
        self.assertAlmostEqual(sa, sb)

    def test_bundle_roots_survive_close_camera_minification(self):
        alpha = bundle_atlas(10031)[:256, :, 3]
        root = alpha[:8].mean(0)
        starts = np.flatnonzero(np.diff(np.r_[False, root > .5, False]))
        widths = starts[1::2]-starts[::2]
        self.assertGreaterEqual(widths.min(), 10)
        self.assertGreater(root.mean(), .20)
        self.assertLess(root.mean(), .65)

    def test_bundle_roots_survive_hero_mask_mipmaps(self):
        alpha = bundle_atlas(10031)[:256, :, 3]
        filtered = alpha[:32].reshape(32, 8, 128).mean(axis=(0, 2))
        self.assertGreaterEqual(int((filtered > .5).sum()), 4)

    def test_fragment_reduction_keeps_nine_hull_vertices(self):
        rng = np.random.default_rng(10111)
        points = rng.normal(size=(24, 3))
        points /= np.linalg.norm(points, axis=1)[:, None]
        result = compact(points)
        self.assertEqual(result.shape, (9, 3))
        bm = bmesh.new()
        for p in result:
            bm.verts.new(p)
        bmesh.ops.convex_hull(bm, input=list(bm.verts))
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        self.assertEqual(len(bm.faces), 14)
        bm.free()

    def test_exposed_foam_is_closed_and_inside_each_physical_gash(self):
        import bpy
        from sofa_pass11 import foam_core
        from sofa_pass11_mesh import gash_field
        specs = {
            'SeatCushion_C': dict(centre=[0, -.295, .43], tangent=[1, 0, 0],
                across=[0, 1, 0], half_length=.118, half_width=.048, seed=9801, height_min=.408),
            'BackCushion_C': dict(centre=[0, .1, .535], tangent=[0, 0, 1],
                across=[1, 0, 0], half_length=.07, half_width=.035, seed=9912, depth_max=.128),
        }
        for name, spec in specs.items():
            with self.subTest(name=name):
                obj = foam_core(name, spec, None)
                positions = np.array([v.co[:] for v in obj.data.vertices])
                self.assertTrue((gash_field(positions, spec) < 0).all())
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                self.assertTrue(all(edge.is_manifold for edge in bm.edges))
                self.assertGreater(abs(bm.calc_volume()), .000001)
                self.assertEqual(len(bm.faces), 144)
                bm.free()
                bpy.data.objects.remove(obj, do_unlink=True)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DetailTests))
    if not result.wasSuccessful():
        raise RuntimeError('Pass-11 detail controls failed')
