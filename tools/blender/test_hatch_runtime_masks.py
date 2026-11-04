"""Runtime mask fields must not bake photographic grain into atlas UVs."""
import importlib.util
from pathlib import Path
import unittest
import bpy

spec = importlib.util.spec_from_file_location("build_hatch", Path(__file__).with_name("build_hatch.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class RuntimeMasksTest(unittest.TestCase):
    def test_runtime_masks_have_no_photographic_dependency(self):
        material = build.material()
        fields = build.build_weather(material)
        for key in ("layer_masks", "weather_masks", "geometry_normal"):
            self.assertIn(key, fields)
            pending = [fields[key].node]
            visited = set()
            while pending:
                node = pending.pop()
                if node in visited:
                    continue
                visited.add(node)
                self.assertFalse(node.type == "TEX_IMAGE" and node.image and
                                 Path(node.image.filepath).suffix.lower() in (".jpg", ".png"),
                                 key + " contains photographic detail")
                pending.extend(link.from_node for socket in node.inputs for link in socket.links)

result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeMasksTest))
if not result.wasSuccessful():
    raise RuntimeError("runtime mask probes failed")
