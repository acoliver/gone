"""Small numeric controls for the exported-geometry verifier, without Blender."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
import trimesh

from verify import ROOT, clean, geometry_buffers, penetration, same_geometry, silhouette, uv_loss


def sheet():
    mesh = trimesh.Trimesh(vertices=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
                           faces=[[0, 1, 2], [0, 2, 3]], process=False)
    mesh.visual = trimesh.visual.TextureVisuals(uv=np.array([[0, 0], [1, 0], [1, 1], [0, 1]]))
    return mesh


class ExportMeasurements(unittest.TestCase):
    def test_tear_area_has_zero_loss_for_unchanged_and_half_for_one_removed_triangle(self):
        before = sheet()
        self.assertAlmostEqual(uv_loss(before, before, 256), 0)
        torn = before.submesh([[0]], append=True)
        self.assertAlmostEqual(uv_loss(before, torn, 256), .5, delta=.01)

    def test_geometry_equality_detects_vertex_change(self):
        before = sheet()
        after = before.copy()
        self.assertTrue(same_geometry(before, after))
        after.vertices[0, 0] += .0001
        self.assertFalse(same_geometry(before, after))

    def test_raw_buffer_check_detects_normals_and_uv_changes(self):
        scratch = ROOT / 'tmp/age'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            a, b = Path(directory) / 'a.glb', Path(directory) / 'b.glb'
            before = sheet()
            before.export(a)
            before.copy().export(b)
            self.assertEqual(geometry_buffers(a), geometry_buffers(b))
            after = before.copy()
            after.visual.uv[0, 0] = .2
            after.export(b)
            self.assertNotEqual(geometry_buffers(a), geometry_buffers(b))
            after = before.copy()
            normals = before.vertex_normals.copy()
            normals[0] = [0, 1, 0]
            after.vertex_normals = normals
            after.export(b, include_normals=True)
            before.export(a, include_normals=True)
            self.assertNotEqual(geometry_buffers(a), geometry_buffers(b))

    def test_silhouette_controls(self):
        before = sheet()
        self.assertEqual(silhouette([before], [before], 200), 1)
        after = before.copy()
        after.apply_translation([2, 0, 0])
        self.assertEqual(silhouette([before], [after], 200), 0)

    def test_penetration_detects_overlap_and_clearance(self):
        before = trimesh.creation.box()
        after = before.copy()
        after.apply_translation([.5, 0, 0])
        self.assertGreater(penetration(clean(before), clean(after)), .1)
        after.apply_translation([1, 0, 0])
        self.assertEqual(penetration(before, after), 0)


if __name__ == '__main__':
    unittest.main()
