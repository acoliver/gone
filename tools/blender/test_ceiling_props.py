"""Check fitted service meshes in the same Y-up frame used by Godot."""
import json
import struct
from pathlib import Path
import unittest

import bpy

ROOT = Path(__file__).resolve().parents[2]


class CeilingPropsTest(unittest.TestCase):
    def test_fitted_meshes_have_one_surface_and_stay_in_budget(self):
        manifest = json.loads((ROOT / 'assets/props/ceiling/manifest.json').read_text())
        for name, budget in {'detector': 3000, 'sprinkler': 3000, 'duct': 2000}.items():
            with self.subTest(name=name):
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.gltf(filepath=str(ROOT / f'assets/props/ceiling/{name}.glb'))
                meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
                self.assertEqual(len(meshes), 1)
                mesh = meshes[0].data
                mesh.calc_loop_triangles()
                self.assertEqual(len(mesh.materials), 1)
                # Blender discards degenerate faces on import; GPU budgets count
                # the original GLB index buffer, including those submitted faces.
                raw = (ROOT / f'assets/props/ceiling/{name}.glb').read_bytes()
                length = struct.unpack_from('<I', raw, 12)[0]
                document = json.loads(raw[20:20 + length])
                submitted = sum(document['accessors'][part['indices']]['count'] // 3
                                for source in document['meshes'] for part in source['primitives'])
                self.assertEqual(submitted, manifest[name]['triangles'])
                self.assertLessEqual(submitted, budget)
                self.assertLessEqual(len(mesh.loop_triangles), budget)
                points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
                for axis in range(3):
                    self.assertAlmostEqual(min(p[axis] for p in points), -.5, places=5)
                    self.assertAlmostEqual(max(p[axis] for p in points), .5, places=5)
                if name == 'duct':
                    # Blender's Z is runtime Y, and Blender's Y is runtime -Z.
                    body_top = .30 / .35 - .5
                    for height in [-.5, body_top]:
                        for depth in [-.40 / .44 / 2, .40 / .44 / 2]:
                            for end in [-.5, .5]:
                                self.assertTrue(any(abs(p.x - end) < 1e-6 and abs(p.y - depth) < 1e-6
                                                    and abs(p.z - height) < 1e-6 for p in points))
                    flat_body = [face for face in mesh.polygons if face.area > .35]
                    self.assertGreaterEqual(len(flat_body), 8)
                    for face in flat_body:
                        self.assertAlmostEqual(max(abs(v) for v in face.normal), 1, places=5)

    def test_generated_fixture_has_metric_mount_and_separate_textured_glass(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path = ROOT / 'assets/props/ceiling/fixture.glb'
        bpy.ops.import_scene.gltf(filepath=str(path))
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        self.assertEqual(len(meshes), 4)
        self.assertFalse(any(obj.type in ('LIGHT', 'CAMERA') for obj in bpy.context.scene.objects))
        points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
        # Native Blender +Z is exported glTF +Y. The top seats directly at zero.
        for axis, limits in enumerate([(-.55, .55), (-.11, .11), (-.10, 0)]):
            self.assertAlmostEqual(min(p[axis] for p in points), limits[0], places=5)
            self.assertAlmostEqual(max(p[axis] for p in points), limits[1], places=5)
        triangles = 0
        glass = []
        for obj in meshes:
            obj.data.calc_loop_triangles()
            triangles += len(obj.data.loop_triangles)
            self.assertEqual(len(obj.data.materials), 1)
            material = obj.data.materials[0]
            if material.name == 'RecessedFrostedGlass':
                glass.append(obj)
                shader = material.node_tree.nodes.get('Principled BSDF')
                self.assertTrue(shader.inputs['Emission Color'].is_linked)
                self.assertEqual(shader.inputs['Emission Strength'].default_value, 3)
                self.assertLess(max((obj.matrix_world @ v.co).z for v in obj.data.vertices), -.08)
        self.assertEqual(triangles, 2664)
        self.assertLessEqual(triangles, 3000)
        self.assertEqual(len(glass), 1)
        manifest = json.loads((ROOT / 'assets/props/ceiling/manifest.json').read_text())
        self.assertEqual(manifest['fixture']['triangles'], triangles)
        self.assertNotIn('module', manifest)
        self.assertFalse((path.parent / 'module.glb').exists())


if __name__ == '__main__':
    unittest.main(argv=['test_ceiling_props'], exit=True)
