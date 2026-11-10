"""Closed SDF output and reproducible, non-planar height-field controls."""
import unittest

import numpy as np
import trimesh

from residue_sdf import field, mesh_sdf, height_field, filled_proxy


class ResidueSDF(unittest.TestCase):
    def test_seeded_height_is_not_flat(self):
        x = np.linspace(-.1, .1, 101)
        a, _ = height_field(x, x, 95)
        b, _ = height_field(x, x, 95)
        self.assertTrue(np.array_equal(a, b))
        self.assertGreater(np.std(a[10:-10, 10:-10]), .002)
        self.assertTrue(np.all(a[[0, -1]] == 0))

    def test_marching_cubes_is_closed_and_outward(self):
        sdf, origin, voxel = field(.12, .14, .003, 95)
        vertices, faces, _ = mesh_sdf(sdf, origin, voxel)
        mesh = trimesh.Trimesh(vertices, faces, process=True)
        self.assertTrue(mesh.is_watertight)
        self.assertGreater(mesh.volume, 0)
        self.assertLess(np.max(mesh.extents[:2]), .17)
        self.assertLess(mesh.bounds[1, 2], .035)


    def test_proxy_keeps_surface_height_without_pore_handles(self):
        sdf, origin, voxel = field(.12, .14, .003, 95)
        v, f, _ = filled_proxy(sdf, origin, voxel)
        mesh = trimesh.Trimesh(v, f, process=True)
        self.assertTrue(mesh.is_watertight)
        self.assertEqual(mesh.euler_number, 2)
        self.assertLess(mesh.bounds[1, 2], .035)

    def test_full_size_proxy_has_one_closed_shell_without_pore_handles(self):
        sdf, origin, voxel = field(seed=9501)
        v, f, _ = filled_proxy(sdf, origin, voxel)
        mesh = trimesh.Trimesh(v, f, process=True)
        self.assertTrue(mesh.is_watertight)
        self.assertEqual(mesh.euler_number, 2)
        self.assertGreater(mesh.volume, 0)
        self.assertGreater(mesh.bounds[0, 2], 0)


if __name__ == '__main__':
    unittest.main()
