"""Blender regressions for fitted back panels and export-safe decay materials."""
from pathlib import Path
import sys
import unittest

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import surface_tree
from densify import densify
from foam_collapse import largest_shell
from grain_paths import surface_walk
from sofa_full_decay import SOURCE, open_cover_bottom


class BackHem(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with bpy.data.libraries.load(str(SOURCE), link=False) as (_, target):
            target.objects = ['BackCushion_C']
        self.obj = target.objects[0]
        bpy.context.collection.objects.link(self.obj)
        self.obj.modifiers.clear()
        largest_shell(self.obj)

    def test_opening_is_confined_to_actual_bottom_not_downward_front_bulge(self):
        open_cover_bottom(self.obj, True)
        densify(self.obj, 2)
        bm = bmesh.new()
        bm.from_mesh(self.obj.data)
        heights = [(self.obj.matrix_world@v.co).z for edge in bm.edges if edge.is_boundary for v in edge.verts]
        self.assertTrue(heights)
        self.assertLess(max(heights), .46)
        point = Vector((-.014, .188, .646))
        _, _, _, distance = surface_tree(self.obj).find_nearest(point)
        self.assertLess(distance, .004)
        bm.free()

    def test_grain_walk_crosses_front_after_bottom_is_opened(self):
        open_cover_bottom(self.obj, True)
        densify(self.obj, 2)
        path = surface_walk(self.obj, (-.12, .18, .65), .16, 9723,
                            step=.004, direction=(1, 0, 0))
        self.assertGreater(len(path), 30)


class RestCarrier(unittest.TestCase):
    def test_real_subdivision_carries_rest_angles_and_is_frozen_once(self):
        import numpy as np
        from cloth_stage import configure
        from fabric_mesh import material, new_object
        from sofa_full_decay import freeze_simulation
        spans = []
        for folded in [False, True, 'simple']:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.context.scene.gravity = (0, 0, 0)
            points = [(x, y, 0) for y in [0, .1, .2] for x in [0, .1, .2]]
            faces = [(j*3+i, j*3+i+1, (j+1)*3+i+1, (j+1)*3+i) for j in range(2) for i in range(2)]
            obj = new_object('RestControl', points, faces, material('Control', (.1, .1, .1)))
            obj.shape_key_add(name='Basis')
            rest = obj.shape_key_add(name='Rest')
            if folded:
                for vertex in rest.data:
                    if vertex.co.x > .1:
                        vertex.co.z = vertex.co.x-.1
                        vertex.co.x = .1
            carrier = obj.modifiers.new('Rest carrier', 'SUBSURF')
            carrier.levels = 1
            if folded == 'simple':
                carrier.subdivision_type = 'SIMPLE'
            mod = configure(obj, dict(frames=60, quality=12, mass=.01, stiffness=150,
                                      bending=2, air_factor=.1), 9, rest_shape=rest)
            mod.settings.mass = .01*9/25
            freeze_simulation(obj, mod, 60)
            self.assertEqual(len(obj.data.vertices), 25)
            self.assertFalse(obj.modifiers)
            self.assertIsNone(obj.data.shape_keys)
            spans.append(float(np.ptp([v.co.z for v in obj.data.vertices])))
        self.assertLess(spans[0], .001)
        self.assertGreater(spans[1], .02)
        self.assertGreater(spans[2], .02)

    def test_part_groups_survive_subdivision_and_restore_original_pivots(self):
        from fabric_mesh import material, new_object
        from sofa_decay_joint import restore_part
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mat = material('Control', (.1, .1, .1))
        points = [(x+offset, y, 0) for offset in [0, 1] for y in [0, .1, .2] for x in [0, .1, .2]]
        faces = [(offset+j*3+i, offset+j*3+i+1, offset+(j+1)*3+i+1, offset+(j+1)*3+i)
                 for offset in [0, 9] for j in range(2) for i in range(2)]
        joint = new_object('Joint', points, faces, mat)
        joint.vertex_groups.new(name='Lip shrink').add(list(range(18)), 1., 'REPLACE')
        joint.vertex_groups.new(name='Part A').add(list(range(9)), 1., 'REPLACE')
        joint.vertex_groups.new(name='Part B').add(list(range(9, 18)), 1., 'REPLACE')
        carrier = joint.modifiers.new('Rest carrier', 'SUBSURF')
        carrier.levels = 1
        deps = bpy.context.evaluated_depsgraph_get()
        frozen = bpy.data.meshes.new_from_object(joint.evaluated_get(deps), depsgraph=deps)
        joint.modifiers.clear()
        joint.data = frozen
        for index, name in enumerate(['A', 'B']):
            obj = new_object(name, [], [], mat)
            obj.location.x = index
            restore_part(joint, obj)
            self.assertEqual(len(obj.data.vertices), 25)
            self.assertAlmostEqual(sum(v.co.x for v in obj.data.vertices)/25, .1, places=5)
            self.assertEqual(obj.location.x, index)
            self.assertEqual(len(obj.data.uv_layers), 1)
            self.assertTrue(all(obj.vertex_groups['Lip shrink'].weight(v.index) > .99 for v in obj.data.vertices))


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
