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


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DetailTests))
    if not result.wasSuccessful():
        raise RuntimeError('Pass-11 detail controls failed')
