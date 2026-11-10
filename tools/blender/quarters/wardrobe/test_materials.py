"""Wardrobe finish contracts, including deliberately broken image controls."""
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import materials


class MaterialTests(unittest.TestCase):
    def test_each_visible_panel_has_an_independent_face(self):
        self.assertEqual(set(materials.FACES), {
            'door-outer', 'door-inner', 'left', 'right', 'back', 'top',
            'bottom', 'frame', 'hardware', 'left-inner', 'right-inner', 'ceiling', 'header'})
        for name, face in materials.FACES.items():
            self.assertGreaterEqual(min(np.array(face['pixels']) / face['size']),
                                    600 if name != 'hardware' else 300)

    def test_constant_and_broad_rust_controls_fail(self):
        face = materials.FACES['door-outer']
        reference = Image.open(materials.ROOT / 'art-source/quarters/locker/faces/door-source.png')
        for colour in [(120, 120, 110), (125, 50, 20)]:
            image = Image.new('RGB', (192, 384), colour)
            with self.assertRaisesRegex(ValueError, 'constant albedo'):
                materials.measure(image, reference, face)

    def test_direct_packing_preserves_generated_rgb(self):
        image = Image.fromarray(np.array([[[80, 89, 85], [125, 61, 23]],
                                         [[110, 112, 105], [93, 40, 19]]], np.uint8))
        packed, normal, orm = materials.channels(image, [.2, .2], hardware=False)
        np.testing.assert_array_equal(np.asarray(packed)[..., :3], np.asarray(image))
        self.assertEqual(normal.size, image.size)
        self.assertTrue(np.isfinite(np.asarray(normal)).all())
        self.assertTrue((np.asarray(orm)[..., 1] >= 175).all())

    def test_relief_comes_from_the_generated_image(self):
        image = Image.new('RGB', (32, 32), (89, 95, 90))
        _, normal, _ = materials.channels(image, [.2, .2], hardware=False)
        np.testing.assert_array_equal(np.asarray(normal)[..., :2], 128)

    def test_mean_calibration_does_not_amplify_reference_grain(self):
        rng = np.random.default_rng(95)
        colours = np.full((64, 64, 3), [100, 110, 105], dtype=float)
        colours[:, :10] = [112, 60, 30]
        raw = Image.fromarray(np.uint8(colours + rng.integers(-1, 2, (64, 64, 1))))
        reference = Image.fromarray(np.uint8(colours + rng.integers(-18, 19, (64, 64, 1))))
        image, metadata = materials.calibrate_means(raw, reference)
        broad_paint = np.asarray(image, float)[10:-10, 20:-10]
        self.assertLess(float(broad_paint.std((0, 1)).max()), 3)
        self.assertEqual(np.asarray(metadata['lab_affine_matrix']).shape, (3, 3))

    def test_no_green_gate_detects_saturated_green(self):
        self.assertGreater(materials.green_fraction(Image.new('RGB', (32, 32), (20, 120, 35))), .99)
        self.assertEqual(materials.green_fraction(Image.new('RGB', (32, 32), (100, 105, 99))), 0)

    def test_material_thresholds_reject_each_failed_contract(self):
        passing = dict(delta_e=2., paint_mean_delta_e=2., paint_std_delta_e=2.,
                       rust_mean_delta_e=2., rust_std_delta_e=2.,
                       planar_light_gradient=.01, secondary_autocorrelation=.2,
                       edge_broad_ratio=3., no_green=0., pixels_per_metre=700.)
        self.assertTrue(materials.face_passes(passing))
        for metric, value in dict(delta_e=9., paint_mean_delta_e=9.,
                                  secondary_autocorrelation=.51, edge_broad_ratio=1.79,
                                  no_green=.006, pixels_per_metre=599.,
                                  planar_light_gradient=.061).items():
            with self.subTest(metric=metric):
                self.assertFalse(materials.face_passes(dict(passing, **{metric: value})))

if __name__ == '__main__':
    unittest.main()
