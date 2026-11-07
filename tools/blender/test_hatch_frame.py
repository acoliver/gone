"""Delivered generated-frame fitting, measured against a fresh simulation export."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hatch_fit as fit

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art-source/hatch/hunyuan"


class FrameFitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = ROOT / "tmp/hunyuan-hatch/slice2e"
        scratch.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="frame-test-", dir=scratch)
        output = Path(cls.temp.name) / "contract.json"
        subprocess.run(["godot", "--headless", "--path", str(ROOT), "-s", "tools/export_hatch_parts.gd", "--", "--output", str(output)], check=True)
        cls.contract = json.loads(output.read_text())
        cls.vertices, cls.faces = fit.read_source_glb(SOURCE / "C-s410-sv.glb")
        cls.recipe = json.loads((SOURCE / "C-s410-sv-selection.json").read_text())
        cls.hatch = fit.fit_frame(cls.contract, cls.vertices, cls.faces, cls.recipe)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_ring_retains_every_named_reservation_and_both_exported_loops(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            targets = variant["fit"]["ring"]
            self.assertEqual(set(result.ring), set(targets["reservation_ids"]))
            all_points = np.concatenate([region.vertices for region in result.ring.values()])
            for loop in (targets["inner"], targets["outer"]):
                for target in np.asarray(loop):
                    self.assertLessEqual(np.linalg.norm(all_points[:, :2] - target[:2], axis=1).min(), 1e-6)
    def test_only_visible_front_relief_fills_the_approved_22_mm(self):
        # The driver replaced the whole-tube minimum scale with this measured
        # front-relief contract. Hidden source depth is discarded, not crushed.
        for variant, result in zip(self.contract["variants"], self.hatch):
            points = np.concatenate([region.vertices for region in result.ring.values()])
            depth = points[:, 2] if variant["hinge_sign"] > 0 else .2 - points[:, 2]
            self.assertAlmostEqual(depth.min(), -.028, delta=1e-6)
            self.assertAlmostEqual(depth.max(), -.006, delta=1e-6)
            self.assertGreater(result.source_relief_plane, float(self.vertices[:, 2].min()))
            for region in result.ring.values():
                retained = self.vertices[self.faces[region.source_faces], 2]
                self.assertTrue((retained.max(axis=1) >= result.source_relief_plane - 1e-7).all(), "hidden back faces are discarded")
            self.assertGreater(result.depth_scale_ratio, 0)

    def test_source_cut_has_an_outward_rear_seating_surface(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            area = 0.0
            for solid in variant["frame_solids"]:
                if solid["id"] not in result.ring:
                    continue
                region = result.ring[solid["id"]]
                rear = solid["transform"]["origin"][2] + variant["hinge_sign"] * solid["size"][2] / 2
                tri = region.vertices[region.faces]
                cap = (abs(tri[:, :, 2] - rear) < 1e-7).all(axis=1)
                self.assertTrue((region.normals[cap, 2] * variant["hinge_sign"] > .999999).all())
                area += float(np.linalg.norm(np.cross(tri[cap, 1] - tri[cap, 0], tri[cap, 2] - tri[cap, 0]), axis=1).sum() / 2)
            self.assertGreater(area, .4, "discarding the hidden tube must close its annular cut, not leave reverse fasteners over an open shell")

    def test_every_rivet_head_stands_five_mm_proud_of_the_actual_band(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            heights = fit.measure_rivet_relief(result, variant)
            self.assertEqual(len(heights), 108)
            self.assertGreaterEqual(min(heights), .005)

    def test_bead_cross_section_retains_a_rounded_crown(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            profile = fit.measure_bead_profile(result, variant)
            self.assertGreaterEqual(profile["depth_levels"], 5)
            self.assertGreaterEqual(profile["flank_normal_levels"], 5)
            self.assertGreater(profile["crown_rise_m"], .005)

    def test_interfaces_never_project_in_front_of_the_generated_surface(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            self.assertLessEqual(fit.measure_interface_excess(result, variant), 1e-6)


    def test_positive_triangles_have_complete_nonoverlapping_semantic_coverage(self):
        for result in self.hatch:
            for region in result.ring.values():
                points = region.vertices[region.faces]
                areas = np.linalg.norm(np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]), axis=1)
                self.assertTrue((areas > 0).all(), region.id)
                self.assertEqual(len(np.unique(region.faces)), len(region.vertices), "no invisible extrema")
                self.assertEqual(len(region.source_faces), len(region.faces), "every fitted triangle has raw source ancestry")

    def test_actual_vertices_stay_in_their_oriented_reservation(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            for solid in variant["frame_solids"]:
                if solid["id"] not in result.ring:
                    continue
                region = result.ring[solid["id"]]
                basis = np.asarray(solid["transform"]["basis"]).T
                local = (region.vertices - solid["transform"]["origin"]) @ basis
                self.assertTrue((np.abs(local) <= np.asarray(solid["size"]) / 2 + .001).all(), solid["id"])
                section = np.asarray(solid["section"])
                edges = np.roll(section, -1, axis=0) - section
                offsets = local[:, None, :2] - section
                distances = (edges[:, 0] * offsets[:, :, 1] - edges[:, 1] * offsets[:, :, 0]) / np.linalg.norm(edges, axis=1)
                self.assertTrue((distances >= -.001).all() or (distances <= .001).all(), "no triangle bridges two ring reservations")

    def test_generated_mounts_stay_inside_the_actual_clipped_outline(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            for solid in variant["frame_solids"]:
                if solid["id"] not in result.hardware or not solid["section"]:
                    continue
                local = (result.hardware[solid["id"]].vertices - solid["transform"]["origin"]) @ np.array(solid["transform"]["basis"]).T
                section = np.asarray(solid["section"])
                edges = np.roll(section, -1, axis=0) - section
                offset = local[:, None, :2] - section
                distances = (edges[:, 0] * offset[:, :, 1] - edges[:, 1] * offset[:, :, 0]) / np.linalg.norm(edges, axis=1)
                self.assertTrue((distances >= -.001).all() or (distances <= .001).all(), solid["id"] + " cannot use its unclipped AABB")

    def test_source_barrel_seals_the_existing_hinge_return_gap(self):
        # The return now stops at four fixed knuckles. Keep the grazing ray's
        # original offsets from each exported seam and test every knuckle.
        for variant, result in zip(self.contract["variants"], self.hatch):
            for solid in variant["frame_solids"]:
                if not solid["id"].startswith("HINGE/KNUCKLE-"):
                    continue
                bottom = solid["transform"]["origin"][1] - solid["size"][1] / 2
                eye = np.array([-.4, bottom + .09, -1.9])
                target = np.array([-.6, bottom + .01, .1])
                if variant["hinge_sign"] < 0:
                    eye[2], target[2] = .2-eye[2], .2-target[2]
                direction = target-eye
                region = result.hardware[solid["id"]]
                tri = region.vertices[region.faces]
                e1, e2 = tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
                p = np.cross(direction, e2)
                det = np.einsum("ij,ij->i", e1, p)
                live = abs(det) > 1e-15
                e1, e2, p, det, tri = e1[live], e2[live], p[live], det[live], tri[live]
                off = eye-tri[:, 0]
                q = np.cross(off,e1)
                u = np.einsum("ij,ij->i",off,p)/det
                v = q@direction/det
                t = np.einsum("ij,ij->i",e2,q)/det
                self.assertTrue(((u>=0)&(v>=0)&(u+v<=1)&(t>=0)&(t<=2)).any(), "source barrel must fill the reserved hinge gap: " + solid["id"])

    def test_original_hinge_attachment_is_not_left_in_the_ring(self):
        hinge = next(row for row in self.recipe["regions"] if row["role"] == "hinge_mount")
        points = self.vertices[self.faces[hinge["faces"]]]
        lower, upper = points[:, :, 1].min(), points[:, :, 1].max()
        axis = self.vertices[hinge["landmarks"]["axis_bottom"] + hinge["landmarks"]["axis_top"]]
        tangent = 2 * axis[:, 0].mean() - points[:, :, 0].max()
        for frame in self.hatch:
            for region in frame.ring.values():
                centres = self.vertices[self.faces[region.source_faces]].mean(axis=1)
                original_mount = ((centres[:, 0] > tangent) & (centres[:, 1] > lower) & (centres[:, 1] < upper))
                self.assertFalse(original_mount.any(), "relocating two stations must also remove the original central mount from the generated ring")

    def test_four_fixed_knuckles_and_all_rivets_are_source_derived(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            self.assertEqual(len(result.hinges), 4)
            self.assertEqual(len(result.rivets), 108)
            for station, region in zip(variant["fit"]["hinge_stations"], result.hinges):
                self.assertEqual(region.id, station["reservation_id"])
                centre = np.asarray(station["transform"]["origin"])
                self.assertLessEqual(abs((region.vertices[:, 1].min() + region.vertices[:, 1].max()) / 2 - centre[1]), 1e-6)
                self.assertGreater(len(region.source_faces), 0)
            for target, region in zip(variant["frame_rivets"], result.rivets):
                self.assertEqual(region.id, target["id"])
                self.assertGreater(len(region.source_faces), 0)

    def test_source_rivet_heads_face_outward_on_both_sides(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            count = len(result.rivets) // 2
            for index in range(count):
                front_target, rear_target = variant["frame_rivets"][index], variant["frame_rivets"][index + count]
                front = (result.rivets[index].vertices - front_target["transform"]["origin"]) @ np.asarray(front_target["transform"]["basis"])
                rear = (result.rivets[index + count].vertices - rear_target["transform"]["origin"]) @ np.asarray(rear_target["transform"]["basis"])
                np.testing.assert_allclose(front, rear * [1, -1, 1], atol=1e-6)

    def test_normals_are_finite_outward_and_the_generated_bead_is_not_a_box(self):
        for result in self.hatch:
            for region in result.ring.values():
                self.assertTrue(np.isfinite(region.normals).all())
                np.testing.assert_allclose(np.linalg.norm(region.normals, axis=1), 1, atol=1e-6)
            depth = np.concatenate([region.vertices[:, 2] for region in result.ring.values()])
            self.assertGreater(len(np.unique(np.round(depth, 6))), 20, "source relief survives fitting")

    def test_interfaces_keep_required_seal_ids_and_square_normals(self):
        for variant, result in zip(self.contract["variants"], self.hatch):
            self.assertEqual(set(result.interfaces), set(variant["fit"]["required_seal_ids"]))
            self.assertEqual(fit.validate_fit(result, variant).seal_misses, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
