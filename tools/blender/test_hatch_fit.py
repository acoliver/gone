"""Source/fit boundary rejection tests. Runs in Python or pinned Blender."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hatch_fit as fit

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art-source/hatch/hunyuan"


class SourceValidationTest(unittest.TestCase):
    def setUp(self):
        self.vertices = np.array([[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.]])
        self.faces = np.array([[0, 1, 2], [0, 2, 3]])
        self.digest = "a" * 64
        self.recipe = {"schema_version": 1, "source_sha256": self.digest,
                       "registration": np.eye(4).tolist(), "discarded_faces": [],
                       "regions": [{"role": "ring", "faces": [0, 1],
                                    "landmarks": {"inner_loop": [0, 1], "outer_loop": [2, 3]},
                                    "target_reservations": ["SURROUND/FORE/RING/000"]}]}
        self.reservations = {"SURROUND/FORE/RING/000"}

    def validate(self):
        return fit.validate_source(self.vertices, self.faces, self.recipe, self.digest, self.reservations)

    def test_valid_source_retains_every_positive_area_triangle(self):
        self.assertEqual(self.validate()["assigned_triangles"], 2)

    def test_hash_mismatch(self):
        self.recipe["source_sha256"] = "b" * 64
        with self.assertRaisesRegex(fit.FitError, "source hash"):
            self.validate()

    def test_absent_landmark(self):
        del self.recipe["regions"][0]["landmarks"]["inner_loop"]
        with self.assertRaisesRegex(fit.FitError, "landmark"):
            self.validate()

    def test_unknown_reservation(self):
        self.recipe["regions"][0]["target_reservations"] = ["invented"]
        with self.assertRaisesRegex(fit.FitError, "reservation"):
            self.validate()

    def test_empty_region(self):
        self.recipe["regions"][0]["faces"] = []
        with self.assertRaisesRegex(fit.FitError, "empty region"):
            self.validate()

    def test_nan_vertex(self):
        self.vertices[0, 0] = np.nan
        with self.assertRaisesRegex(fit.FitError, "finite"):
            self.validate()

    def test_nan_registration(self):
        self.recipe["registration"][0][0] = np.nan
        with self.assertRaisesRegex(fit.FitError, "registration"):
            self.validate()

    def test_degenerate_triangle_requires_explicit_removal(self):
        self.faces[0] = [0, 0, 1]
        with self.assertRaisesRegex(fit.FitError, "degenerate"):
            self.validate()
        self.recipe["discarded_faces"] = [0]
        self.recipe["regions"][0]["faces"] = [1]
        self.assertEqual(self.validate()["discarded_triangles"], 1)

    def test_positive_area_triangle_cannot_be_silently_discarded(self):
        self.recipe["discarded_faces"] = [0]
        self.recipe["regions"][0]["faces"] = [1]
        with self.assertRaisesRegex(fit.FitError, "positive-area"):
            self.validate()

    def test_unassigned_triangle(self):
        self.recipe["regions"][0]["faces"] = [0]
        with self.assertRaisesRegex(fit.FitError, "unassigned"):
            self.validate()

    def test_overlapping_source_selections(self):
        self.recipe["regions"].append(copy.deepcopy(self.recipe["regions"][0]))
        with self.assertRaisesRegex(fit.FitError, "overlap"):
            self.validate()

    def test_invalid_face_index(self):
        self.faces[0, 2] = 4
        with self.assertRaisesRegex(fit.FitError, "index"):
            self.validate()

    def test_unsupported_schema(self):
        self.recipe["schema_version"] = 2
        with self.assertRaisesRegex(fit.FitError, "schema"):
            self.validate()

    def test_manifest_missing_source_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {"schema_version": 1, "files": {"raw.glb": hashlib.sha256(b"raw").hexdigest()}}
            with self.assertRaisesRegex(fit.FitError, "missing"):
                fit.validate_manifest(root, manifest)
            (root / "raw.glb").write_bytes(b"different")
            with self.assertRaisesRegex(fit.FitError, "hash"):
                fit.validate_manifest(root, manifest)
            (root / "raw.glb").write_bytes(b"raw")
            fit.validate_manifest(root, manifest)

    def test_frozen_frame_fixture_has_explicit_topology_and_identity(self):
        manifest = json.loads((SOURCE / "provenance.json").read_text())
        fit.validate_manifest(SOURCE, manifest)
        self.assertEqual(manifest["selected"], "C-s410-sv")
        self.assertEqual(manifest["alternative"], "C-s412-sv")
        self.assertEqual(manifest["model"]["revision"], "3a761b539b29fe4ff64714813aa9560fd66f5de0")
        self.assertEqual(len(manifest["generator"]["commit"]), 40)
        for name, count in (("C-s410-sv", 277912), ("C-s412-sv", 268304)):
            vertices, faces = fit.read_source_glb(SOURCE / (name + ".glb"))
            self.assertEqual(len(faces), count)
            recipe = json.loads((SOURCE / (name + "-selection.json")).read_text())
            report = fit.validate_source(vertices, faces, recipe, manifest["files"][name + ".glb"],
                                         {name for region in recipe["regions"] for name in region["target_reservations"]})
            self.assertEqual(report["assigned_triangles"] + report["discarded_triangles"], count)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful():
        raise SystemExit(1)
