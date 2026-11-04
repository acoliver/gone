"""Verify the authoring graph uses photographic PBR inputs, not noise colours."""
import importlib.util
from pathlib import Path
import unittest
import bpy

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("build_hatch", HERE / "build_hatch.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ScanFinishTest(unittest.TestCase):
    def test_photo_colour_normal_and_roughness_feed_the_actual_bake_graph(self):
        material = build.material()
        fields = build.build_weather(material)
        nodes = material.node_tree.nodes
        files = [Path(n.image.filepath).name for n in nodes if n.type == "TEX_IMAGE" and n.image]
        for file in ("rusty_metal_04_albedo.jpg", "green_metal_rust_albedo.jpg", "r3-rust_coarse_01-albedo.jpg",
                     "rusty_metal_04_normal.jpg", "green_metal_rust_normal.jpg", "r3-rust_coarse_01-normal.jpg",
                     "rusty_metal_04_orm.jpg", "green_metal_rust_orm.jpg", "rusty_painted_metal_orm.jpg"):
            self.assertIn(file, files)
        self.assertFalse(any(n.type == "TEX_NOISE" for n in nodes), "no noise-authored camouflage colour")
        for field in ("albedo", "roughness", "metallic", "height", "curvature"):
            self.assertIn(field, fields)
        attributes = {n.attribute_name for n in nodes if n.type == "ATTRIBUTE"}
        self.assertTrue({"relief", "chip_edge", "painted", "substrate", "frame_normal"}.issubset(attributes))


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScanFinishTest))
if not result.wasSuccessful():
    raise RuntimeError("scan finish probes failed")
