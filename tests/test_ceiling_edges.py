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

    def test_gate_requires_all_four_circuit_and_camera_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = Image.new('RGB', (2304, 1296), (32, 28, 24))
            for circuit in ('secondary-white', 'emergency'):
                for view in ('connector-bulkhead', 'hall-end-wall'):
                    image.save(root / f'{circuit}-{view}.png')
            results, failures = EDGES.check(root)
            self.assertEqual(len(results), 4)
            self.assertEqual(failures, [])
            image.paste((0, 0, 0), EDGES.BAND)
            image.save(root / 'secondary-white-connector-bulkhead.png')
            _, failures = EDGES.check(root)
            self.assertEqual(len(failures), 1)
            self.assertIn('secondary-white-connector-bulkhead: black fraction', failures[0])
            (root / 'emergency-hall-end-wall.png').unlink()
            with self.assertRaises(FileNotFoundError):
                EDGES.check(root)

    def test_wrong_resolution_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.png'
            Image.new('RGB', (1152, 648)).save(path)
            with self.assertRaisesRegex(ValueError, '2304 x 1296'):
                EDGES.fractions(path)
