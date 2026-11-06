"""Blender-side reduction and reflected registration regression tests."""
import json
import math
import os
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_hatch as build
import hatch_fit as fit
from hatch_generated_frame import local_region, reduce_region

ROOT = Path(__file__).resolve().parents[2]


class GeneratedFrameTest(unittest.TestCase):
    def test_reduced_seating_land_hides_rear_cap_from_mouth(self):
        from hatch_generated_frame import load_frames, reduce_ring
        source = Path(os.environ.get("HATCH_SOURCE_JSON", ROOT / "assets/props/hatch/parts.json"))
        document = json.loads(source.read_text())
        frames = load_frames(document)
        scale = math.tan(math.radians(23)) * 2 / 1312
        for variant, frame in zip(document["variants"], frames):
            reduced = reduce_ring(frame, variant, build.mesh_object, build.material())
            for solid in variant["frame_solids"]:
                if solid["id"] not in reduced:
                    continue
                local = (reduced[solid["id"]].vertices - solid["transform"]["origin"]) @ np.asarray(solid["transform"]["basis"]).T
                self.assertLessEqual(float((abs(local) - np.asarray(solid["size"]) / 2).max()), .001, "shared cleanup preserves each semantic reservation: " + solid["id"])
            points = np.concatenate([region.vertices for region in reduced.values()])
            offsets = np.cumsum([0] + [len(region.vertices) for region in list(reduced.values())[:-1]])
            faces = np.concatenate([region.faces + offset for region, offset in zip(reduced.values(), offsets)])
            tree = BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)
            into = variant["hinge_sign"]
            origin = Vector((0, 1.28, .1 - into * 3.75))
            for pixel in [180, 181]:
                direction = Vector((-.5 * scale, -(pixel - 656) * scale, into)).normalized()
                hit, normal, _, _ = tree.ray_cast(origin, direction, 8)
                self.assertIsNotNone(hit, "continuous source seating land hides its rear cap")
                self.assertGreater(normal.dot(-direction), 0, "source underside faces the camera without normal steering")
                self.assertLess(normal.y, -.9, "the retained source land is the downward soffit, not the annular rear cap")

    def test_atlas_preserves_positive_submicrometre_cut_triangles(self):
        # A reservation cut can leave a real triangle narrower than float32 UV
        # precision at the smart-project island's original atlas position.
        points = [[0, 0, 0], [1, 0, 0], [0, 1, 0],
                  [-.042694211, .028261529, -.032232404],
                  [-.042694207, .028261315, -.032232404],
                  [-.042694211, .028260900, -.032232285]]
        obj = build.mesh_object("CutTriangle", points, [[0, 1, 2], [3, 4, 5]],
                                None, build.Matrix.Identity(4), build.material())
        build.atlas([obj], 2048)
        for polygon in obj.data.polygons:
            uv = np.array([obj.data.uv_layers.active.data[i].uv[:] for i in polygon.loop_indices])
            self.assertGreater(abs(np.linalg.det((uv[1:] - uv[0]).T)), 0)
        self.assertEqual(len(obj.data.polygons), 2, "no discarded positive-area cuts")
        bpy.data.objects.remove(obj, do_unlink=True)

    def test_reflected_local_registration_preserves_outward_normals(self):
        region = fit.FittedRegion("reflection", [[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 1, 2]], [0])
        pose = dict(origin=[0, 0, 0], basis=[[1, 0, 0], [0, 1, 0], [0, 0, -1]])
        vertices, faces = local_region(region, pose)
        local = fit.FittedRegion("local", vertices, faces, [0])
        np.testing.assert_allclose(local.normals, [[0, 0, -1]], atol=1e-12)

    def test_generated_rivet_reduction_preserves_real_extrema(self):
        source = ROOT / "art-source/hatch/hunyuan"
        vertices, faces = fit.read_source_glb(source / "C-s410-sv.glb")
        recipe = json.loads((source / "C-s410-sv-selection.json").read_text())
        row = next(row for row in recipe["regions"] if row["role"] == "rivets")
        selected = np.asarray(row["faces"])
        center = vertices[row["landmarks"]["template_centre"][0]]
        selected = selected[np.linalg.norm(vertices[faces[selected]].mean(axis=1)[:, :2] - center[:2], axis=1) < .05]
        points, triangles, ancestry = fit.close_selection(vertices, faces, selected, "rivet")
        region = fit.FittedRegion("rivet", points, triangles, ancestry)
        pose = dict(origin=[0, 0, 0], basis=np.eye(3).tolist())
        low, indices, high = reduce_region(region, pose, 48, build.mesh_object, None, build.material())
        self.assertLessEqual(len(indices), 48)
        np.testing.assert_allclose(np.min(low, axis=0), points.min(axis=0), atol=1e-6)
        np.testing.assert_allclose(np.max(low, axis=0), points.max(axis=0), atol=1e-6)
        self.assertEqual(len(np.unique(indices)), len(low))
        fit.FittedRegion("low", low, indices, np.zeros(len(indices), dtype=int))
        bpy.data.objects.remove(high, do_unlink=True)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeneratedFrameTest))
    if not result.wasSuccessful():
        raise SystemExit(1)
