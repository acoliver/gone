"""Blender regressions for pass-8 opacity and bounded clearance."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fabric_mesh import material, new_object
from opacity_bake import opacity_bake
from sofa_pass8_finish import clearance
from sofa_pass8_mesh import mesh_quality

ROOT = Path(__file__).resolve().parents[3]


class Pass8Tests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_opacity_uses_texel_distance_not_zero_vertex_distances(self):
        obj = new_object('Square', [(0, 0, 0), (.1, 0, 0), (.1, .1, 0), (0, .1, 0)],
                         [(0, 1, 2, 3)], material('Cloth', (.3, .3, .3)))
        layer = obj.data.uv_layers.new(name='BakeUV')
        for loop, point in zip(layer.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop.uv = point
        image, report = opacity_bake(obj, ROOT/'tmp/age/pass8/test-opacity.png', size=128)
        pixels = np.array(image.pixels[:]).reshape(128, 128, 4)
        self.assertTrue(np.all(pixels[16:-16, 16:-16, 0] == 1))
        self.assertGreater(report['transparent_texels'], 0)
        self.assertIn('per-texel', report['distance_method'])

    def test_clearance_preserves_rigid_and_bounds_displacement(self):
        mat = material('Control', (.3, .3, .3))
        rigid = new_object('Rigid', [(-1, -1, 0), (1, -1, 0), (0, 1, 0)], [(0, 1, 2)], mat)
        cloth = new_object('Cloth', [(-.1, 0, -.0005), (.1, 0, .0005), (0, .1, .0005)], [(0, 1, 2)], mat)
        original = np.array([v.co[:] for v in cloth.data.vertices])
        fixed = np.array([v.co[:] for v in rigid.data.vertices])
        report = clearance([cloth, rigid], {'Cloth'})
        self.assertGreater(report['counts'][0], 0, report)
        self.assertTrue(report['pass'], report)
        np.testing.assert_array_equal(fixed, [v.co[:] for v in rigid.data.vertices])
        self.assertLessEqual(np.linalg.norm(np.array([v.co[:] for v in cloth.data.vertices])-original, axis=1).max(), .003001)

    def test_quality_rejects_sliver_without_excluding_it(self):
        obj = new_object('Sliver', [(0, 0, 0), (.1, 0, 0), (.05, .00001, 0)],
                         [(0, 1, 2)], material('Control', (.3, .3, .3)))
        result = mesh_quality(obj)
        self.assertFalse(result['pass'])
        self.assertFalse(result['self_collision_exclusions'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Pass8Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError('Pass-8 regressions failed')
