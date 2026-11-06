"""The whole generated wheel must survive the delivered tangent pipeline."""
import json
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_hatch as build
from hatch_bake import validate_mesh_attributes
from hatch_generated_parts import GeneratedParts

ROOT = Path(__file__).resolve().parents[2]


def rim_radii(points, faces):
    """Intersect projected triangle edges, not a convex hull hiding dents."""
    edges = points[faces[:, [0, 1, 1, 2, 2, 0]]].reshape(-1, 2, 3)[:, :, :2]
    radii = []
    for angle in np.radians(np.arange(360)):
        direction = np.array([np.cos(angle), np.sin(angle)])
        signed = edges[:, :, 0] * direction[1] - edges[:, :, 1] * direction[0]
        crossing = (signed[:, 0] * signed[:, 1] <= 0) & (signed[:, 0] != signed[:, 1])
        line, distance = edges[crossing], signed[crossing]
        weight = distance[:, 0] / (distance[:, 0] - distance[:, 1])
        intersections = line[:, 0] + weight[:, None] * (line[:, 1] - line[:, 0])
        radii.append(float((intersections @ direction).max()))
    return np.asarray(radii)


class GeneratedPartsTest(unittest.TestCase):
    def test_delivered_wheel_rim_stays_within_two_mm_over_full_rotation(self):
        from hatch_bake import CINV
        document = json.loads((ROOT / 'assets/props/hatch/parts.json').read_text())
        bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/props/hatch/hatch.glb'))
        names = [name for name, row in document['nodes'].items()
                 if row.get('id') in ('Wheel/hub', 'ReverseWheel/hub')]
        self.assertEqual(len(names), 4)
        high = np.load(ROOT / 'art-source/hatch/hunyuan/parts/wheel-high.npz')
        reference = rim_radii(high['vertices'], high['faces'])
        # The generated rim itself varies by about 6 mm. Limit reduction's added
        # radial error to 2 mm, under 0.7% of its 321.5 mm outside radius.
        for name in names:
            obj = bpy.data.objects[name]
            points = np.asarray([tuple((CINV @ v.co.to_4d())[:3]) for v in obj.data.vertices])
            faces = np.asarray([tuple(face.vertices) for face in obj.data.polygons])
            self.assertLessEqual(len(faces), 4000, name)
            radii = rim_radii(points, faces)
            error = float(np.abs(radii - reference).max())
            print('DELIVERED_RIM', name, 'triangles', len(faces), 'max_radial_error_m', error)
            self.assertLessEqual(error, .002, name)
            np.testing.assert_allclose(radii, np.roll(radii, 60), atol=1e-6, rtol=0)

    def test_reduced_whole_wheel_has_exact_bounds_positive_faces_and_unit_tangents(self):
        document = {'generated_sources': {}, 'fit_recipe': {}}
        source = GeneratedParts(document)
        record = json.loads((source.root / 'wheel-fit.json').read_text())
        part = dict(id='Wheel/hub', shape='generated_wheel', size=record['size'])
        material = build.material()
        points, faces, high, _ = source.geometry(part, None, build.mesh_object, material)
        points, faces = np.asarray(points), np.asarray(faces)
        np.testing.assert_allclose(points.min(0), -np.asarray(record['size']) / 2, atol=1e-6, rtol=0)
        np.testing.assert_allclose(points.max(0), np.asarray(record['size']) / 2, atol=1e-6, rtol=0)
        triangles = points[faces]
        self.assertTrue((np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) > 0).all())
        self.assertEqual(len(np.unique(faces)), len(points), 'only submitted vertices define the wheel bounds')
        obj = build.mesh_object('WholeWheelTangentRegression', points, faces, None, build.Matrix.Identity(4), material)
        build.atlas([obj], 2048)
        validate_mesh_attributes([obj], {obj.name: dict(kind='leaf')}, 2048)
        bpy.data.objects.remove(high, do_unlink=True)
        bpy.data.objects.remove(obj, do_unlink=True)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeneratedPartsTest))
    if not result.wasSuccessful():
        raise SystemExit(1)
