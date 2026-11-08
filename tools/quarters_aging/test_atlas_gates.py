import tempfile
import unittest
from pathlib import Path
import numpy as np
import trimesh
from atlas_gates import uv_metrics
from streak_sources import write_sources

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT / 'tmp/mat/locker/pass2'


class AtlasGateTests(unittest.TestCase):
    def test_exported_uv_gate_detects_stretch_hidden_by_equal_area(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            mesh = trimesh.Trimesh(vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[0, 1, 2]], process=False)
            uv = np.array([[0, 0], [.15, 0], [0, .15]])
            mesh.visual = trimesh.visual.TextureVisuals(uv=uv)
            path = Path(folder) / 'isometric.glb'
            mesh.export(path)
            result = uv_metrics(path)
            self.assertLess(result['max_stretch'], 1.015)
            self.assertAlmostEqual(result['density_min'], 307.2, places=3)
            uv[:, 0] *= 2
            uv[:, 1] /= 2
            mesh.visual = trimesh.visual.TextureVisuals(uv=uv)
            mesh.export(path)
            result = uv_metrics(path)
            self.assertGreater(result['max_stretch'], 3.99)
            self.assertLess(result['density_min'], 304.6 * .85)

    def test_float_source_export_is_seeded_and_preserves_negative_positions(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        sources = [dict(position_blender=[-.295, -.30, 1.2])]
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            a, b = Path(folder) / 'a.tres', Path(folder) / 'b.tres'
            write_sources(a, sources, 9501)
            write_sources(b, sources, 9501)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertIn('"format": "RGBAFloat"', a.read_text())
            self.assertIn('"height": 2', a.read_text())


if __name__ == '__main__':
    unittest.main()
