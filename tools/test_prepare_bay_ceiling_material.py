"""Geometry-aware bake contracts, independent of lighting or visual approval."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import prepare_bay_ceiling_material as bake

ROOT = Path(__file__).resolve().parents[1]


class CeilingBakeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit = bake.FittedGuides(json.loads((ROOT / 'art-source/bay-ceiling/source-guide.json').read_text()))

    def test_colour_transfer_roundtrips_source_srgb(self):
        source = np.linspace(0, 1, 301)
        np.testing.assert_allclose(bake.srgb(bake.linearize(source)), source, atol=1e-7)

    def test_each_variant_masks_its_own_exact_outline(self):
        with patch.object(bake, 'WIDTH', 512), patch.object(bake, 'HEIGHT', 256):
            slot_distance = bake.edge_distance(self.fit.slots)
            variation = np.ones((256, 512))
            dust_field = np.zeros((256, 512))
            intact_coverage = bake.polygon_inside(self.fit.outer, self.fit.slots)
            for name in ('intact', 'subtlewarp', 'sag', 'torncorner', 'brokenedge'):
                coverage, oxide, lip, dust = bake.variant_masks(self.fit, name, slot_distance, variation, dust_field)
                expected = bake.polygon_inside(self.fit.damaged_outer(name), self.fit.slots)
                np.testing.assert_array_equal(coverage, expected)
                for mask in (oxide, lip, dust):
                    self.assertTrue(np.all(mask[~coverage] == 0))
                    self.assertGreater(mask[coverage].max(), 0)
                if name in ('torncorner', 'brokenedge'):
                    self.assertGreater(np.count_nonzero(intact_coverage & ~coverage), 500)
                    distance = bake.edge_distance([self.fit.damaged_outer(name), *self.fit.slots])
                    np.testing.assert_allclose(lip, np.exp(-np.square(distance / .0022)) * coverage)

    def test_u_height_ramp_uses_opengl_hatch_normal_convention(self):
        width, height = 128, 64
        u_m = np.arange(width) * bake.WIDTH_M / width
        oxide = np.broadcast_to(u_m / bake.WIDTH_M, (height, width))
        zeros = np.zeros_like(oxide)
        with patch.object(bake, 'WIDTH', width), patch.object(bake, 'HEIGHT', height):
            _, _, normal = bake.relief_maps(oxide, zeros, zeros, zeros)
        expected = np.array([-.00016 / bake.WIDTH_M, 0, 1])
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(normal, np.broadcast_to(expected, normal.shape), atol=1e-7)
        self.assertLess(normal[32, 64, 0], 0)

    def test_v_height_ramp_accounts_for_descending_image_rows_once(self):
        width, height = 128, 64
        v_m = (height - 1 - np.arange(height)) * bake.HEIGHT_M / height
        oxide = np.broadcast_to((v_m / bake.HEIGHT_M)[:, None], (height, width))
        zeros = np.zeros_like(oxide)
        with patch.object(bake, 'WIDTH', width), patch.object(bake, 'HEIGHT', height):
            points = bake.image_points([(0, -.1), (0, .1)])
            self.assertGreater(points[0][1], points[1][1])
            _, _, normal = bake.relief_maps(oxide, zeros, zeros, zeros)
        # A rising +V surface tilts its OpenGL normal toward -V, as in prepare_hatch_paint.py.
        expected = np.array([0, -.00016 / bake.HEIGHT_M, 1])
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(normal, np.broadcast_to(expected, normal.shape), atol=1e-7)
        self.assertLess(normal[32, 64, 1], 0)

    def test_damaged_variants_have_fixed_localized_broad_wear(self):
        with patch.object(bake, 'WIDTH', 512), patch.object(bake, 'HEIGHT', 256):
            slot_distance = bake.edge_distance(self.fit.slots)
            variation = np.full((256, 512), .78)
            dust_field = np.zeros((256, 512))
            masks = {}
            for name in ('intact', 'subtlewarp', 'sag', 'torncorner', 'brokenedge'):
                coverage, oxide, _, _ = bake.variant_masks(self.fit, name, slot_distance, variation, dust_field)
                masks[name] = oxide
                fraction = np.mean(oxide[coverage] > .12)
                self.assertLess(fraction, .43, 'charcoal stays dominant')
                # The new square mounting flange adds painted area to the denominator.
                # Pin the unchanged recipe on that exact new contour instead of restyling it.
                expected = {'intact': .1994808103, 'subtlewarp': .2033492823,
                            'sag': .2690115036, 'torncorner': .2761454659,
                            'brokenedge': .2702235015}
                self.assertAlmostEqual(fraction, expected[name], places=7)
                again = bake.variant_masks(self.fit, name, slot_distance, variation, dust_field)[1]
                np.testing.assert_array_equal(oxide, again)
            self.assertFalse(np.array_equal(masks['sag'], masks['brokenedge']))


if __name__ == '__main__':
    unittest.main()
