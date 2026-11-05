"""Focused geometry probes, run with Blender --background --python-exit-code 1."""
import importlib.util
import json
from pathlib import Path
import unittest

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_hatch", Path(__file__).with_name("build_hatch.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class HatchConstructionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        cls.document = json.loads((ROOT / "assets/props/hatch/parts.json").read_text())
        cls.objects, cls.nodes, cls.error = build.construct(cls.document, build.material())
        cls.by_name = {obj.name: obj for obj in cls.objects}

    def test_coaming_roundover_preserves_the_lower_corner_seal(self):
        for variant in self.document["variants"]:
            solid = next(row for row in variant["frame_solids"] if row["id"] == "COAMING")
            vertices, faces = build.collar_geometry(solid)
            origin = Vector(solid["transform"]["origin"])
            into = variant["hinge_sign"]
            eye = Vector((.4, .6, .1 - into * 2)) - origin
            target = Vector((-.5, .12, .1)) - origin
            tree = BVHTree.FromPolygons(vertices, faces)
            hit, _, _, _ = tree.ray_cast(eye, (target - eye).normalized(), 6)
            self.assertIsNotNone(hit, "coaming seals the oblique lower hinge corner")

    def test_thick_slab_does_not_scale_paint_relief_or_edge_bevel(self):
        for variant in self.document["variants"]:
            for group in variant["groups"]:
                for part in group["parts"]:
                    if not part["id"].endswith("Steel/plate"):
                        continue
                    self.assertEqual(part["paint_layer_depth"], .002)
                    self.assertEqual(part["edge_bevel"], .004)
                    vertices, _ = build.geometry(part, True)
                    count = len(part["contour"])
                    front = -part["size"][2] / 2
                    self.assertAlmostEqual(vertices[2 * count][2] - front, .004, delta=1e-7)
                    self.assertTrue(any(abs(point[2] - front - .002) < 1e-7 for point in vertices))

    def test_spokes_have_elliptic_sections_not_flat_bars(self):
        for variant in self.document["variants"]:
            for group in variant["groups"]:
                for part in group["parts"]:
                    if "/spoke-" not in part["id"]:
                        continue
                    vertices, _ = build.geometry(part, group["steel"])
                    sx, sy, sz = part["size"]
                    diagonal = [(abs(x) / (sx / 2), abs(z) / (sz / 2)) for x, y, z in vertices
                                if abs(y) < sy * .49 and .1 < abs(x) / (sx / 2) < .95 and .1 < abs(z) / (sz / 2) < .95]
                    self.assertGreater(len(diagonal), 8, part["id"])
                    self.assertTrue(all(abs(x*x + z*z - 1) < 1e-5 for x, z in diagonal), part["id"])

    def test_lifted_islands_have_camera_scale_width_and_relief(self):
        part = self.document["variants"][0]["groups"][0]["parts"][0]
        vertices, _ = build.geometry(part, True)
        base_count = len(build.rounded_outline(part["size"], part["radius"])) * 5
        islands = vertices[base_count:]
        self.assertGreater(len(islands), 400)
        relief = max(v[2] for v in islands) - min(v[2] for v in islands)
        # Andrew changed the solid slab thickness; its paint keeps the existing 1 mm floor.
        self.assertGreaterEqual(relief, .001)
        spans = [max(v[0] for v in islands[i:i+8]) - min(v[0] for v in islands[i:i+8])
                 for i in range(0, len(islands), 8)]
        self.assertGreater(min(spans), min(part["size"][:2]) * .015)
        self.assertLess(max(spans), min(part["size"][:2]) * .06)

    def test_paint_tiles_form_two_connected_sheets_without_isolated_strips(self):
        part = self.document["variants"][0]["groups"][0]["parts"][0]
        vertices, _ = build.geometry(part, True)
        start = len(build.rounded_outline(part["size"], part["radius"])) * 5
        tiles = [{tuple(round(value, 7) for value in point) for point in vertices[i+4:i+8]}
                 for i in range(start, len(vertices), 8)]
        remaining = set(range(len(tiles)))
        components = []
        while remaining:
            connected = {remaining.pop()}
            pending = list(connected)
            while pending:
                current = pending.pop()
                neighbors = {other for other in remaining if len(tiles[current] & tiles[other]) >= 2}
                remaining -= neighbors
                connected |= neighbors
                pending.extend(neighbors)
            components.append(connected)
        self.assertEqual(sorted(map(len, components)), [44, 44],
                         "raised paint must form sheets, not separate diagonal flecks")

    def test_every_raised_sheet_top_faces_out_of_the_leaf(self):
        obj = self.by_name["v0_g00_p000"]
        size = self.document["variants"][0]["groups"][0]["parts"][0]["size"]
        # Paint relief stays independent of Andrew's thicker slab.
        part = self.document["variants"][0]["groups"][0]["parts"][0]
        front = -size[2] / 2 + part["paint_layer_depth"] * .10
        checked = 0
        for face in obj.data.polygons:
            points = [build.CINV @ obj.data.vertices[index].co.to_4d() for index in face.vertices]
            if not all(abs(point.z - front) < 1e-7 for point in points):
                continue
            checked += 1
            self.assertLess((build.CINV.to_3x3() @ face.normal).z, -.999999,
                            "open interior tile top faces into the paint")
        self.assertGreater(checked, 100)

    def test_annular_cells_have_no_internal_radial_walls(self):
        for name, row in self.nodes.items():
            if row["kind"] != "frame":
                continue
            solid = self.document["variants"][row["variant"]]["frame_solids"][row["part"]]
            if not solid["section"] or not solid["id"].startswith("SURROUND/"):
                continue
            vertices = [build.CINV @ v.co.to_4d() for v in self.by_name[name].data.vertices]
            for start, end in ((0, 3), (1, 2)):
                a, b = (Vector(solid["section"][i]) for i in (start, end))
                edge = b - a
                for face in self.by_name[name].data.polygons:
                    points = [vertices[i] for i in face.vertices]
                    if max(p.z for p in points) - min(p.z for p in points) < 1e-6:
                        continue
                    distances = [abs(edge.x * (p.y-a.y) - edge.y * (p.x-a.x)) / edge.length for p in points]
                    self.assertFalse(max(distances) < 1e-6, name + " contains an internal radial wall")

    def test_annular_bevels_meet_at_shared_radial_boundaries(self):
        for variant in self.document["variants"]:
            for role in ("/RING/", "/LIP/"):
                cells = [s for s in variant["frame_solids"] if role in s["id"]]
                for index, cell in enumerate(cells):
                    following = cells[(index + 1) % len(cells)]
                    vertices, _ = build.annular_geometry(cell)
                    next_vertices, _ = build.annular_geometry(following)
                    origin, next_origin = (Vector(s["transform"]["origin"]) for s in (cell, following))
                    for ring in range(len(vertices) // 4):
                        for end, start in ((1, 0), (2, 3)):
                            left = Vector(vertices[ring*4+end]) + origin
                            right = Vector(next_vertices[ring*4+start]) + next_origin
                            self.assertLess((left-right).length, 1e-6, cell["id"] + " bevel seam")

    def test_unchanged_face_return_does_not_hide_the_paint_substrate(self):
        from mathutils.bvhtree import BVHTree
        for variant in self.document["variants"]:
            for side in (0, 1):
                entries = [(name, row) for name, row in self.nodes.items()
                           if row["kind"] == "leaf" and row["variant"] == variant["index"] and row["side"] == side]
                plate_name = next(name for name, row in entries if row["id"].endswith("Steel/plate"))
                seal_name = next(name for name, row in entries if row["id"].endswith("/face-return"))
                plate, seal = self.by_name[plate_name], self.by_name[seal_name]
                origin = plate.matrix_world @ (build.C @ Vector((0, 0, -.4, 1))).to_3d()
                direction = plate.matrix_world.to_3x3() @ (build.C.to_3x3() @ Vector((0, 0, 1)))
                distances = []
                for obj in (plate, seal):
                    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
                    tree = BVHTree.FromPolygons(vertices, [tuple(p.vertices) for p in obj.data.polygons], all_triangles=True)
                    hit = tree.ray_cast(origin, direction)
                    self.assertIsNotNone(hit[0], obj.name)
                    distances.append(hit[3])
                self.assertGreater(distances[1] - distances[0], 1e-5, seal_name)

    def test_fixed_and_square_seal_meshes_retain_flat_nondegenerate_normals(self):
        for name, row in self.nodes.items():
            seal = row["kind"] == "leaf" and row["id"].endswith("/face-return")
            if row["kind"] != "frame" and not seal:
                continue
            obj = self.by_name[name]
            for polygon in obj.data.polygons:
                a, b, c = [obj.data.vertices[i].co for i in polygon.vertices]
                normal = (b-a).cross(c-a)
                self.assertGreater(normal.length, 1e-12, name + " degenerate triangle")
                normal.normalize()
                for loop in polygon.loop_indices:
                    self.assertGreater(normal.dot(obj.data.corner_normals[loop].vector), .999999, name)

    def test_square_seal_front_perimeter_faces_outward(self):
        from mathutils.bvhtree import BVHTree
        for name, row in self.nodes.items():
            if row["kind"] != "leaf" or not row["id"].endswith("/face-return"):
                continue
            obj = self.by_name[name]
            part = self.document["variants"][row["variant"]]["groups"][row["group"]]["parts"][row["part"]]
            vertices = [(build.CINV @ vertex.co.to_4d()).to_3d() for vertex in obj.data.vertices]
            tree = BVHTree.FromPolygons(vertices, [tuple(p.vertices) for p in obj.data.polygons], all_triangles=True)
            sign = -1 if row["side"] == 0 else 1
            origin = Vector((0, 0, sign * 2))
            for x in (-part["size"][0] / 2 + .001, 0, part["size"][0] / 2 - .001):
                for y in (-part["size"][1] / 2 + .001, part["size"][1] / 2 - .001):
                    target = Vector((x, y, sign * (part["size"][2] / 2 + .0005)))
                    direction = (target-origin).normalized()
                    hit = tree.ray_cast(origin, direction)
                    self.assertIsNotNone(hit[0], name)
                    self.assertLess(hit[1].dot(direction), 0, name + " inward perimeter")
                    self.assertLessEqual(hit[3], (target-origin).length + .001, name + " recessed perimeter")
            for x in (-part["size"][0]/2, part["size"][0]/2):
                for y in (-part["size"][1]/2, part["size"][1]/2):
                    self.assertTrue(any((v-Vector((x, y, sign*part["size"][2]/2))).length < 1e-7 for v in vertices), name + " exact square corner")

    def test_paint_edges_substrate_and_consistent_rivet_finish_are_attributes(self):
        plate = self.by_name["v0_g00_p000"]
        for name in ("flake", "chip_edge", "substrate", "relief"):
            attribute = plate.data.attributes.get(name)
            self.assertIsNotNone(attribute, name)
            values = [item.value for item in attribute.data]
            self.assertGreater(max(values) - min(values), .1, name)
        finishes = []
        for name, row in self.nodes.items():
            if row["kind"] != "rivet":
                continue
            attribute = self.by_name[name].data.attributes.get("rivet_finish")
            self.assertIsNotNone(attribute)
            finishes.append(tuple(item.value for item in attribute.data))
        self.assertTrue(all(values == finishes[0] for values in finishes))

    def test_leaf_contour_uv_islands_cover_at_least_one_bake_texel(self):
        from bpy_extras.mesh_utils import mesh_linked_uv_islands
        import numpy as np
        build.atlas(self.objects, 2048)
        checked = 0
        for obj in self.objects:
            if self.nodes[obj.name]["id"] != "ForeContour/edge-08":
                continue
            uv = obj.data.uv_layers.active.data
            for island in mesh_linked_uv_islands(obj.data):
                points = np.array([uv[index].uv[:] for face in island for index in obj.data.polygons[face].loop_indices])
                _, axes = np.linalg.eigh(np.cov(points.T))
                span = np.ptp(points @ axes, axis=0)
                self.assertGreaterEqual(min(span) * 2048, 1.0, obj.name + " has subtexel bake islands")
                checked += 1
        self.assertGreater(checked, 0)

    def test_original_bounds_are_preserved(self):
        self.assertLess(self.error, 1e-6)
        for name, row in self.nodes.items():
            if row["kind"] != "frame":
                continue
            solid = self.document["variants"][row["variant"]]["frame_solids"][row["part"]]
            obj = self.by_name[name]
            for vertex in obj.data.vertices:
                source = build.CINV @ vertex.co.to_4d()
                self.assertTrue(all(abs(source[i]) <= solid["size"][i] / 2 + 1e-6 for i in range(3)), name)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(HatchConstructionTest)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise RuntimeError("hatch construction probes failed")
