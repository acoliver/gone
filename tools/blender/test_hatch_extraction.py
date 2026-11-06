"""Bake/interface ownership while the existing construction probes pin behavior."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hatch_bake
import hatch_interfaces

spec = importlib.util.spec_from_file_location("build_hatch", Path(__file__).with_name("build_hatch.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ExtractionTest(unittest.TestCase):
    def test_builder_uses_the_extracted_uv_bake_and_coverage_implementations(self):
        for name in ("painted_coordinates", "atlas", "bake_mesh", "bake_footprints", "verify_bake_coverage", "bake", "final_material"):
            self.assertIs(getattr(build, name), getattr(hatch_bake, name))

    def test_coordinate_conversion_has_one_owner_and_an_exact_inverse(self):
        self.assertIs(build.C, hatch_bake.C)
        self.assertIs(build.CINV, hatch_bake.CINV)
        from mathutils import Matrix
        self.assertEqual(build.C @ build.CINV, Matrix.Identity(4))

    def test_contract_interfaces_use_the_same_extrusion_and_closure_implementation(self):
        for name in ("extrusion", "rounded_outline", "seal_pocket", "collar_geometry", "annular_geometry"):
            self.assertIs(getattr(build, name), getattr(hatch_interfaces, name))

    def test_each_extracted_module_invalidates_reused_bakes(self):
        from unittest.mock import patch
        dependencies = build.build_dependencies()
        self.assertEqual(set(dependencies), {"build_hatch.py", "hatch_bake.py", "hatch_interfaces.py", "hatch_fit.py", "hatch_generated_frame.py"})
        original = Path.read_bytes
        for name in dependencies:
            with self.subTest(module=name):
                def changed(path):
                    return original(path) + (b"\n# changed dependency\n" if path.name == name else b"")
                with patch.object(Path, "read_bytes", changed):
                    self.assertNotEqual(build.build_dependencies(), dependencies)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExtractionTest)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise RuntimeError("hatch helper extraction probes failed")
