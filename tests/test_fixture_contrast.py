import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image

SPEC = importlib.util.spec_from_file_location('fixture_contrast', Path(__file__).resolve().parents[1] / 'tools/check_fixture_contrast.py')
CONTRAST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRAST)


class FixtureContrastTest(unittest.TestCase):
    def measure(self, louvre, slot):
        image = Image.new('RGB', (1200, 900), (slot, slot, slot))
        for index in range(-6, 7):
            x = round(600 + index * .07 * 1000)
            image.paste((louvre, louvre, louvre), (x - 2, 448, x + 3, 453))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.png'
            image.save(path)
            return CONTRAST.measure(path, 1000)

    def test_authored_centres_measure_dark_bars_between_bright_slots(self):
        result = self.measure(26, 220)
        self.assertAlmostEqual(result['display_ratio'], 26 / 220)
        self.assertLess(result['linear_ratio'], result['display_ratio'])
        self.assertTrue(CONTRAST.passes(result))

    def test_washed_out_louvres_fail(self):
        self.assertFalse(CONTRAST.passes(self.measure(130, 220)))

    def test_clipped_slots_fail_even_with_dark_louvres(self):
        self.assertFalse(CONTRAST.passes(self.measure(26, 255)))

    def test_dark_slots_cannot_satisfy_contrast_gate(self):
        self.assertFalse(CONTRAST.passes(self.measure(0, 0)))
