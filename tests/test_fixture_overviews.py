"""Display-space regression for the fixed opening-room camera views."""
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_fixture_overviews import check, within_limit


class FixtureOverviewTest(unittest.TestCase):
    def test_inclusive_fifteen_percent_limit(self):
        self.assertTrue(within_limit(85, 100))
        self.assertTrue(within_limit(115, 100))
        self.assertFalse(within_limit(84.999, 100))
        self.assertFalse(within_limit(115.001, 100))

    def test_every_view_and_camera_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            view = dict(name='emergency-bay-overview', eye='(0, 1, 0)', target='(1, 1, 0)')
            reference = dict(resolution=[16, 9], views=[dict(view, mean_display_luma=100)])
            baseline = root / 'reference.json'
            baseline.write_text(json.dumps(reference))
            manifest = root / 'views.json'
            manifest.write_text(json.dumps([view]))
            image = root / (view['name'] + '.png')
            Image.new('RGB', (16, 9), (100, 100, 100)).save(image)
            self.assertEqual(check(root, baseline)[1], [])
            Image.new('RGB', (16, 9), (84, 84, 84)).save(image)
            self.assertTrue(any('luma' in error for error in check(root, baseline)[1]))
            Image.new('RGB', (16, 9), (116, 116, 116)).save(image)
            self.assertTrue(any('luma' in error for error in check(root, baseline)[1]))
            manifest.write_text(json.dumps([dict(view, eye='(0, 2, 0)')]))
            self.assertTrue(any('camera' in error for error in check(root, baseline)[1]))
            manifest.write_text('[]')
            self.assertTrue(any('missing view' in error for error in check(root, baseline)[1]))
            manifest.write_text(json.dumps([view, view]))
            self.assertTrue(any('duplicate' in error for error in check(root, baseline)[1]))
            manifest.write_text(json.dumps([view]))
            image.unlink()
            self.assertTrue(any('missing image' in error for error in check(root, baseline)[1]))

    @unittest.skipUnless(os.environ.get('FIXTURE_OVERVIEW_CAPTURES'), 'requires native overview captures')
    def test_native_overviews_retain_219a257_display_brightness(self):
        rows, failures = check(Path(os.environ['FIXTURE_OVERVIEW_CAPTURES']))
        self.assertEqual(len(rows), 10)
        self.assertEqual(failures, [])
