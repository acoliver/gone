import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/blender/quarters/sofa'))
from finish_materials import finish_colour, tileable
from atlas_layout import rectangles


class SofaMaterials(unittest.TestCase):
    def test_tiles_are_disjoint_and_padded(self):
        tiles = rectangles([(str(i), 1024, 1024) for i in range(13)] +
                           [('fringe', 512, 1024), ('wool', 512, 1024)] +
                           [(f'dust{i}', 256, 256) for i in range(12)], 4096)
        occupied = np.zeros((4096, 4096), bool)
        for x, y, w, h in tiles.values():
            self.assertFalse(occupied[y:y+h, x:x+w].any())
            occupied[y:y+h, x:x+w] = True
        with self.assertRaises(ValueError):
            rectangles([('too-large', 4097, 4097)], 4096)

    def test_dust_follows_up_faces_and_grime_follows_cavities(self):
        base = np.full((3, 3), .35)
        masks = np.array([[1, 1, 0], [1, 1, 1], [1, .1, 0]])
        aged = finish_colour(base, masks, True, 'fabric')
        self.assertGreater(aged[1].mean(), aged[0].mean())
        self.assertLess(aged[2].mean(), aged[0].mean())
        np.testing.assert_array_equal(finish_colour(base, masks, False, 'fabric'), base)

    def test_weave_edges_are_periodic(self):
        source = np.random.default_rng(95).random((96, 96, 3))
        result = tileable(source)
        np.testing.assert_allclose(result[0], result[-1])
        np.testing.assert_allclose(result[:, 0], result[:, -1])


    def test_generated_illumination_plane_is_removed(self):
        from finish_materials import flatten_illumination
        yy, xx = np.mgrid[:64, :64]
        image = np.dstack([np.full((64, 64), .4)] * 3) * np.exp((xx / 64 - .5) * .4)[..., None]
        result, report = flatten_illumination(image)
        self.assertLess(report['after_linear_gradient'], .002)
        self.assertLess(np.ptp(result.mean((0, 2))), .003)

    def test_weave_removes_broad_bands_but_retains_fine_yarn(self):
        from finish_materials import weave_tile
        yy, xx = np.mgrid[:256, :256]
        band = .12 * np.sin(xx * 2 * np.pi / 128)
        yarn = .04 * np.sin(xx * 2 * np.pi / 4)
        image = np.repeat((.5 + band + yarn)[..., None], 3, axis=2)
        result = weave_tile(image)
        row = result[128, :, 0]
        self.assertLess(abs(np.dot(row - row.mean(), np.sin(np.arange(256) * 2 * np.pi / 128))) / 128, .015)
        self.assertGreater(row.std(), .015)

if __name__ == '__main__':
    unittest.main()
