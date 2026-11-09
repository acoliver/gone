import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image

SPEC = importlib.util.spec_from_file_location('ceiling_edges', Path(__file__).resolve().parents[1] / 'tools/check_ceiling_edges.py')
EDGES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EDGES)


class CeilingEdgesTest(unittest.TestCase):
    def test_fixed_band_counts_black_cutouts_without_counting_dark_steel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.png'
            image = Image.new('RGB', (2304, 1296), (32, 28, 24))
            image.paste((0, 0, 0), (0, 150, 1152, 480))
            image.paste((0, 0, 0), (0, 480, 2304, 1296))
            image.save(path)
            result = EDGES.fractions(path)
            self.assertEqual(result['black_fraction'], 0.5)
            self.assertEqual(result['dark_fraction'], 0.5)

    @staticmethod
    def save_views(root, image):
        for circuit in ('secondary-white', 'emergency'):
            for view in ('connector-bulkhead', 'hall-end-wall', 'duct-collar-2m-connector-side', 'along-connector'):
                image.save(root / f'{circuit}-{view}.png')

    def test_perceptual_regions_reject_red_cutouts_even_above_black_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = Image.new('RGB', (2304, 1296), (110, 25, 7))
            self.save_views(root, image)
            for view, regions in EDGES.REGIONS.items():
                damaged = image.copy()
                for name, box, adjacent in regions:
                    damaged.paste((28, 2, 0), box)
                for circuit in ('secondary-white', 'emergency'):
                    damaged.save(root / f'{circuit}-{view}.png')
            results, failures = EDGES.check(root)
            self.assertEqual(len(failures), 8)
            self.assertTrue(all('luminance ratio' in failure for failure in failures))
            self.assertEqual(results['secondary-white-connector-bulkhead']['black_fraction'], 0)
            self.assertLess(results['secondary-white-duct-collar-2m-connector-side']['regions']['left-duct-end']['luminance_ratio'], 0.3)

    def test_perceptual_regions_reject_an_unlit_region_and_unlit_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.save_views(root, Image.new('RGB', (2304, 1296), (0, 0, 0)))
            _, failures = EDGES.check(root)
            self.assertEqual(sum('luminance ratio' in failure for failure in failures), 8)

    def test_gate_requires_all_eight_circuit_and_camera_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = Image.new('RGB', (2304, 1296), (32, 28, 24))
            self.save_views(root, image)
            results, failures = EDGES.check(root)
            self.assertEqual(len(results), 8)
            self.assertEqual(failures, [])
            image.paste((0, 0, 0), EDGES.BAND)
            image.save(root / 'secondary-white-connector-bulkhead.png')
            _, failures = EDGES.check(root)
            self.assertEqual(len(failures), 2)
            self.assertIn('secondary-white-connector-bulkhead: black fraction', failures[0])
            self.assertIn('secondary-white-connector-bulkhead: rib-front luminance ratio', failures[1])
            (root / 'emergency-hall-end-wall.png').unlink()
            with self.assertRaises(FileNotFoundError):
                EDGES.check(root)

    def test_wrong_resolution_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.png'
            Image.new('RGB', (1152, 648)).save(path)
            with self.assertRaisesRegex(ValueError, '2304 x 1296'):
                EDGES.fractions(path)
