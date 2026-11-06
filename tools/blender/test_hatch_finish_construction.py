"""Geometry and evaluated finish regressions for the hatch, run inside Blender.

The material probes bake its emission onto a UV-mapped source-sized band. They
measure shader output rather than the presence or naming of graph attributes.
"""
import importlib.util
import json
import os
from pathlib import Path
import unittest

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("build_hatch", os.environ.get(
    "HATCH_BUILD_RECIPE", Path(__file__).with_name("build_hatch.py")))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class HatchFinishConstructionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get("HATCH_SOURCE_JSON", ROOT / "assets/props/hatch/parts.json"))
        cls.document = json.loads(source.read_text())
        from hatch_generated_frame import load_frames
        cls.frames = load_frames(cls.document)

    def setUp(self):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def test_lifted_sheets_are_coherent_instead_of_hundreds_of_square_flecks(self):
        for variant in self.document["variants"]:
            for group in variant["groups"]:
                for part in group["parts"]:
                    if not group["steel"] or not part["id"].endswith("Steel/plate"):
                        continue
                    vertices, _ = build.geometry(part, True)
                    start = len(build.rounded_outline(part["size"], part["radius"])) * 5
                    sheets = [vertices[i:i+8] for i in range(start, len(vertices), 8)]
                    self.assertGreater(len(sheets), 50, part["id"])
                    self.assertLessEqual(len(sheets), 100, part["id"] + " scattered flecks")
                    widths = [max(p[0] for p in s) - min(p[0] for p in s) for s in sheets]
                    heights = [max(p[1] for p in s) - min(p[1] for p in s) for s in sheets]
                    self.assertGreaterEqual(min(widths), .030)
                    self.assertGreater(np.median(np.array(heights) / widths), 1.4)
                    for sheet in sheets:
                        self.assertGreater(max(p[2] for p in sheet[:4]) - min(p[2] for p in sheet[4:]), .001)
                        self.assertGreaterEqual(min(p[2] for p in sheet), -part["size"][2] / 2)

    def test_bake_join_preserves_outward_normals_of_reflected_geometry(self):
        material = build.material()
        vertices, faces = build.extrusion([(-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)], .1)
        objects = []
        for sign in (1, -1):
            pose = build.Matrix.Diagonal((sign, 1, 1, 1))
            pose.translation.x = 0 if sign == 1 else 3
            obj = build.mesh_object("ReflectionProbe", vertices, faces, None, pose, material)
            bpy.context.view_layer.update()
            normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
            expected = obj.data.attributes.new("expected_outward", "FLOAT_VECTOR", "FACE")
            for polygon, value in zip(obj.data.polygons, expected.data):
                value.vector = (normal_matrix @ polygon.normal).normalized()
            objects.append(obj)
        joined = build.bake_mesh(objects)
        normal_matrix = joined.matrix_world.to_3x3().inverted().transposed()
        for polygon, value in zip(joined.data.polygons, joined.data.attributes["expected_outward"].data):
            actual = (normal_matrix @ polygon.normal).normalized()
            self.assertGreater(actual.dot(value.vector), .999999,
                               "mirrored bake geometry faces into the steel instead of out of it")

    def test_production_atlas_has_unit_tangents_on_every_constructed_triangle(self):
        objects, _, _ = build.construct(self.document, build.material(), self.frames)
        for resolution in (2048, 4096):
            with self.subTest(resolution=resolution):
                build.atlas(objects, resolution)
                bad = []
                for obj in objects:
                    obj.data.calc_tangents()
                    for loop in obj.data.loops:
                        if abs(loop.tangent.length - 1) > 1e-4:
                            bad.append((obj.name, loop.index, loop.tangent.length))
                self.assertEqual(bad, [], "invalid atlas tangents " + str(bad[:8]))

    def test_weather_field_uses_fasteners_not_zero_radius_pivot_seals(self):
        objects, nodes, _ = build.construct(self.document, build.material(), self.frames)
        # Round 11 splits the zero-radius returns around the fixed knuckles;
        # retain those seal pieces alongside the real fastener controls.
        returns = [obj for obj in objects if "PivotSealSteel/return-" in nodes[obj.name]["id"]]
        fasteners = [obj for obj in objects if nodes[obj.name]["id"].startswith("StrapHinges/ForeSteel/bolt-0-")]
        self.assertTrue(returns, "zero-radius split pivot seals remain in the probe")
        self.assertTrue(fasteners, "real fasteners remain in the probe")
        selected = returns + fasteners
        self.assertGreater(len(selected), 4)
        with np.errstate(divide="raise", invalid="raise"):
            image, _ = build.weather_context(selected, nodes, self.document)
        pixels = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(pixels)
        self.assertTrue(np.all(np.isfinite(pixels)))
        self.assertGreater(float(pixels.reshape(-1, 4)[:, 0].max()), .8,
                           "real fastener blooms disappeared")

    def test_collar_roundovers_collision_reservations_trimmed_rendering_and_both_sided_seals(self):
        # Driver decision replaces drawn-box equality at this guard too. Retain
        # 1 um collision pins, contained/behind-ring render triangles and the
        # unchanged both-sided zero-miss seal/pocket grids, with visible roundovers.
        from hatch_interface_checks import check_interfaces
        document = self.document
        objects, nodes, _ = build.construct(document, build.material(), self.frames)
        check_interfaces(self, build, document, objects, nodes)
        by_name = {obj.name: obj for obj in objects}
        for variant in document["variants"]:
            for solid in variant["frame_solids"]:
                if not (solid["id"].startswith("FRAME/") or solid["id"] == "COAMING"):
                    continue
                points = [build.CINV @ vertex.co.to_4d()
                          for name, row in nodes.items()
                          if row["kind"] == "frame" and row["variant"] == variant["index"] and row["part"] == solid["index"]
                          for vertex in by_name[name].data.vertices]
                self.assertGreater(len({tuple(round(v, 7) for v in p[:3]) for p in points}), 24,
                                   solid["id"] + " still has razor-edged box corners")
                if solid["id"] in ("FRAME/LEFT", "COAMING"):
                    for corner in solid["vertices"]:
                        self.assertGreater(min((p.to_3d() - build.Vector(corner)).length for p in points), .0001,
                                           solid["id"] + " subdivides a square corner without rounding it")

    def test_square_seal_pocket_has_a_rolled_reveal_not_a_vertical_cut(self):
        part = self.document["variants"][0]["groups"][0]["parts"][0]
        size = [part["size"][0], part["size"][1], .010]
        for side in (0, 1):
            vertices, faces = build.seal_pocket(size, part["radius"], .047, side)
            sign = -1 if side == 0 else 1
            front = sign * size[2] / 2
            depths = sorted({round(sign * (front - v[2]), 7) for v in vertices
                             if sign * (front - v[2]) > .000001})
            # Exclude the back of the square backing shell. The pocket itself
            # needs intermediate rings, including a radial as well as axial roll.
            self.assertGreaterEqual(len(depths), 5, "single hard-edged pocket wall")
            count = len(build.rounded_outline(size, part["radius"]))
            front_inner = vertices[2*count:3*count]
            floor = [v for v in vertices if abs(v[2] - (front - sign * .047)) < 1e-7]
            self.assertGreater(max(v[0] for v in front_inner) - max(v[0] for v in floor), .001)
            self.assertTrue(all(len(set(face)) == len(face) for face in faces))

    def bake_field(self, values, field="albedo", resolution=128):
        material = build.material()
        # An XY source plane becomes an upright Blender XZ plane. Coordinate
        # variation and UVs are both explicit, independent of an atlas pack.
        vertices = [(-.375, -.0444, 0), (.375, -.0444, 0),
                    (.375, .0444, 0), (-.375, .0444, 0)]
        obj = build.mesh_object("FinishProbe", vertices, [(0, 1, 2, 3)], None,
                                build.Matrix.Identity(4), material)
        uv = obj.data.uv_layers.new(name="UVMap")
        coordinates = [(0, 0), (1, 0), (1, 1), (0, 1)]
        for loop in obj.data.loops:
            uv.data[loop.index].uv = coordinates[loop.vertex_index]
        for name in ("painted", "hazard", "flake", "chip_edge", "substrate", "frame_ring",
                     "machined", "rivet_finish", "relief", "frame_smooth"):
            build.attr(obj, name, values.get(name, 0))
        build.attr(obj, "band_coordinate", [-1, -1, 1, 1])
        fields = build.build_weather(material)
        tree = material.node_tree
        target = tree.nodes.new("ShaderNodeTexImage")
        image = build.new_image("EvaluatedFinish", resolution)
        target.image = image
        tree.nodes.active = target
        emission = tree.nodes.new("ShaderNodeEmission")
        tree.links.new(fields[field], emission.inputs["Color"])
        tree.links.new(emission.outputs[0], fields["output"].inputs["Surface"])
        scene = bpy.context.scene
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 1
        scene.render.threads_mode = "FIXED"
        scene.render.threads = 4
        scene.render.bake.margin = 0
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.bake(type="EMIT")
        pixels = np.empty(resolution * resolution * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        return pixels.reshape(resolution, resolution, 4)[:, :, :3]

    def test_actual_chip_edge_colour_is_oxide_not_an_overwriting_green_highlight(self):
        colour = self.bake_field({"painted": 1, "chip_edge": 1})
        self.assertGreater(np.median(colour[:, :, 0] / np.maximum(colour[:, :, 1], .0001)), 1.3,
                           "chip colour overwrites the edge corrosion")
        self.assertGreater(float(colour[:, :, 0].std()), .005, "uniform chip colour")

    def test_actual_warning_paint_is_narrower_than_its_steel_carrier(self):
        colour = self.bake_field({"hazard": 1, "painted": 1})
        yellow = ((colour[:, :, 0] > .2) &
                  (colour[:, :, 1] > colour[:, :, 0] * .4) &
                  (colour[:, :, 2] < .06))
        centre = yellow[48:80]
        outside = np.concatenate((yellow[:24], yellow[-24:]))
        self.assertGreater(int(centre.sum()), 20, "warning paint disappeared")
        self.assertEqual(int(outside.sum()), 0, "yellow fills the entire steel carrier")


result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(HatchFinishConstructionTest))
if not result.wasSuccessful():
    raise RuntimeError("hatch finish construction probes failed")
