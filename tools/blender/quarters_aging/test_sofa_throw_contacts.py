"""The throw collides with mechanical surfaces, not alpha cards or duplicate dense covers."""
import sys
import unittest
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_decay_policy import ORDER
from sofa_decay_throw import install_contacts


class ThrowContacts(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.required = {'Frame', 'Feet', 'Rivets', 'DecayFloor'}
        self.required.update(n+suffix for n in ORDER for suffix in ['_GameContact', '_Residue'])
        for name in self.required | {'SeatCushion_C', 'SeatCushion_C_Fringe', 'Throw'}:
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata([(0, 0, 0), (.1, 0, 0), (0, .1, 0)], [], [(0, 1, 2)])
            obj = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(obj)
            obj['aged_export'] = True

    def test_exact_pool_excludes_alpha_cards_and_duplicate_dense_surfaces(self):
        values = install_contacts()
        self.assertEqual(set(values), self.required)
        install_contacts()
        for obj in bpy.context.scene.objects:
            collisions = [m for m in obj.modifiers if m.type == 'COLLISION']
            self.assertEqual(len(collisions), int(obj.name in self.required))

    def test_floor_is_a_closed_unexported_slab_with_unchanged_contact_height(self):
        install_contacts()
        floor = bpy.data.objects['DecayFloor']
        self.assertEqual(len(floor.data.polygons), 6)
        self.assertEqual(len(floor.data.vertices), 8)
        self.assertAlmostEqual(max(v.co.z for v in floor.data.vertices), 0.)
        self.assertAlmostEqual(min(v.co.z for v in floor.data.vertices), -.1)
        self.assertFalse(floor['aged_export'])
        self.assertTrue(floor.hide_render)
        self.assertEqual(floor.collision.cloth_friction, 8.)

    def test_missing_settled_surface_fails_before_starting_the_solve(self):
        bpy.data.objects.remove(bpy.data.objects['BackCushion_R_Residue'], do_unlink=True)
        with self.assertRaisesRegex(ValueError, 'BackCushion_R_Residue'):
            install_contacts()
        self.assertTrue(all(not obj.modifiers for obj in bpy.context.scene.objects))


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
