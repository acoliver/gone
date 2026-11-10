"""Regression controls for classification, variation and existing-UV rasterization."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from map_library import ROOT, classify_face, choose_face, triangle_samples, projection_frame, map_prop


class LibraryMappingTests(unittest.TestCase):
    def test_upward_face_is_top_even_when_narrow(self):
        self.assertEqual(classify_face([0, 0, 1], [.04, 1], .04), 'top')
        self.assertEqual(classify_face([0, 0, -1], [.5, 1], .5), 'broad')

    def test_area_and_aspect_select_strip(self):
        self.assertEqual(classify_face([0, -1, 0], [.04, 1], .04), 'strip')
        self.assertEqual(classify_face([0, -1, 0], [.05, .05], .0025), 'strip')
        self.assertEqual(classify_face([0, -1, 0], [.5, 1], .5), 'broad')

    def test_seeded_choice_avoids_neighbor_and_prefers_aspect(self):
        rows = [dict(id='a', kind='broad', pixels=[400, 800]),
                dict(id='b', kind='broad', pixels=[400, 800]),
                dict(id='c', kind='broad', pixels=[800, 400])]
        a = choose_face(rows, 'broad', [.5, 1], 95, 'Door', set())
        self.assertEqual(a, choose_face(rows, 'broad', [.5, 1], 95, 'Door', set()))
        b = choose_face(rows, 'broad', [.5, 1], 95, 'NextDoor', {a['id']})
        self.assertNotEqual(a['id'], b['id'])
        self.assertNotEqual(b['id'], 'c')

    def test_absent_class_fails(self):
        with self.assertRaises(ValueError):
            choose_face([], 'top', [1, 1], 1, 'test', set())

    def test_uv_triangle_pixel_centres_and_barycentric_interpolation(self):
        uv = np.array([[0, 0], [1, 0], [0, 1]])
        x, y, weights = triangle_samples(uv, 8)
        self.assertTrue(len(x) > 0)
        reconstructed = weights @ uv
        np.testing.assert_allclose(reconstructed[:, 0], (x+.5)/8)
        np.testing.assert_allclose(reconstructed[:, 1], 1-(y+.5)/8)
        np.testing.assert_allclose(weights.sum(1), 1)
        self.assertTrue((weights >= -1e-8).all())

    def test_degenerate_uv_fails(self):
        with self.assertRaises(ValueError):
            triangle_samples(np.zeros((3, 2)), 8)

    def test_atlas_bytes_repeat_and_true_uv_overlap_fails(self):
        scratch = ROOT / 'tmp/mat2'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as name:
            library = Path(name)
            pixels = np.zeros((640, 640, 3), np.uint8)+[90, 100, 95]
            pixels[:80, :, :] = [85, 35, 20]
            Image.fromarray(pixels.astype(np.uint8)).save(library / 'panel.png')
            Image.new('RGB', (4, 4), (90, 100, 95)).save(library / 'clean.png')
            manifest = dict(faces=[dict(id='panel', kind='broad', pixels=[640, 640],
                                       image='panel.png', passed=True)],
                            clean='clean.png', hardware='panel.png', fabric='panel.png')
            (library / 'manifest.json').write_text(json.dumps(manifest))
            face = dict(id='panel/0', part='panel', material='PaintedSteel', normal=[0, -1, 0],
                        triangles=[[[0, 0, 0], [1, 0, 0], [0, 0, 1]],
                                   [[1, 0, 0], [1, 0, 1], [0, 0, 1]]],
                        uv=[[[0, 0], [1, 0], [0, 1]], [[1, 0], [1, 1], [0, 1]]])
            document = dict(blend='fixture.blend', materials=['PaintedSteel'], faces=[face])
            with patch('map_library.LIBRARY', library):
                map_prop(document, 'fixture', library/'first', 32, 95)
                map_prop(document, 'fixture', library/'second', 32, 95)
                for path in (library/'first').iterdir():
                    self.assertEqual(path.read_bytes(), (library/'second'/path.name).read_bytes())
                duplicate = dict(face, id='overlapping/0')
                document['faces'].append(duplicate)
                with self.assertRaisesRegex(ValueError, 'UV overlap'):
                    map_prop(document, 'fixture', library/'invalid', 32, 95)
                left, right = np.array(face['uv'], float), np.array(face['uv'], float)
                left[..., 0] *= .515625
                right[..., 0] = .515625+right[..., 0]*(1-.515625)
                document['faces'] = [dict(face, id='left/0', uv=left.tolist()),
                                     dict(face, id='right/0', uv=right.tolist())]
                result = map_prop(document, 'fixture', library/'shared-edge', 32, 95)
                self.assertEqual(result['uv_overlap_texels'], 0)

    def test_selection_requires_source_density_at_the_actual_face_size(self):
        rows = [dict(id='thin', kind='top', pixels=[1536, 512]),
                dict(id='supported', kind='top', pixels=[1536, 1024])]
        for seed in range(16):
            chosen = choose_face(rows, 'top', [2.14, 1.04], seed, 'tabletop', set())
            self.assertEqual(chosen['id'], 'supported')
        with self.assertRaisesRegex(ValueError, 'source density'):
            choose_face(rows[:1], 'top', [2.14, 1.04], 95, 'tabletop', set())

    def test_projection_uses_world_up_on_vertical_panel(self):
        points = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 2], [0, 0, 2]])
        projected, size = projection_frame(points, [0, -1, 0])
        np.testing.assert_allclose(size, [1, 2])
        np.testing.assert_allclose(projected[:, 1], [0, 0, 1, 1])


if __name__ == '__main__':
    unittest.main()
