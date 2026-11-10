"""Run in Blender: diagnostic contacts must end on the actual comparison mesh."""
import sys
import unittest
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from neighbour_colliders import morph_contact, slide


def panel(name, y, bottom):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-.2,y,bottom), (.2,y,bottom), (.2,y,bottom+.4), (-.2,y,bottom+.4)], [], [(0,1,2,3)])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


class NeighbourContacts(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_morph_starts_on_fitted_surface_and_ends_on_comparison_vertices(self):
        fitted = panel('Fitted', .3, .4)
        comparison = panel('Comparison', .2, .2)
        expected = np.array([v.co[:] for v in comparison.data.vertices])
        proxy = morph_contact(comparison, fitted, 30)
        bpy.context.scene.frame_set(1)
        evaluated = proxy.evaluated_get(bpy.context.evaluated_depsgraph_get())
        initial = np.array([v.co[:] for v in evaluated.data.vertices])
        np.testing.assert_allclose(initial[:,1], .3, atol=1e-6)
        self.assertGreaterEqual(initial[:,2].min(), .4-1e-6)
        bpy.context.scene.frame_set(30)
        evaluated = proxy.evaluated_get(bpy.context.evaluated_depsgraph_get())
        np.testing.assert_allclose(np.array([v.co[:] for v in evaluated.data.vertices]), expected, atol=1e-6)
        np.testing.assert_allclose(np.array([v.co[:] for v in comparison.data.vertices]), expected)
        self.assertFalse(any(m.type == 'COLLISION' for m in comparison.modifiers))
        self.assertFalse(proxy['aged_export'])

    def test_rear_approach_starts_clear_and_returns_to_actual_transform(self):
        obj = panel('Comparison', .2, .2)
        expected = obj.location.copy()
        slide(obj, 1.2, 40, 100, axis=1)
        bpy.context.scene.frame_set(1)
        self.assertAlmostEqual(obj.location.y, expected.y+1.2, places=6)
        bpy.context.scene.frame_set(100)
        np.testing.assert_allclose(obj.location[:], expected[:], atol=1e-6)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
