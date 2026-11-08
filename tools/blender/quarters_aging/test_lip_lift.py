"""Unmeasurable short fragments cannot contribute evidence of lifted lips."""
import sys
import unittest
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth_metrics import lip_lift


class LipLift(unittest.TestCase):
    def test_short_fragment_is_counted_as_not_proven_lifted(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new('Short tear fragment')
        mesh.from_pydata([(0, 0, 0), (.006, 0, .001), (.003, .005, 0)], [], [(0, 1, 2)])
        obj = bpy.data.objects.new('Short tear fragment', mesh)
        bpy.context.collection.objects.link(obj)
        obj.vertex_groups.new(name='Lip shrink').add([0, 1, 2], 1., 'REPLACE')
        value = lip_lift(obj)
        self.assertGreater(value['lip_length_m'], 0)
        self.assertEqual(value['unmeasurable_length_m'], value['lip_length_m'])
        self.assertEqual(value['fraction'], 0)
        self.assertFalse(value['pass'])
        self.assertTrue(all(s['lift_m'] is None for s in value['samples']))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LipLift)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise RuntimeError('Lip-lift regression failed')
