"""Visibility requires first-hit coverage and contrast in the lit capture."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from sofa_decay_policy import ORDER
from sofa_pass9_accept import visibility

ROOT = Path(__file__).resolve().parents[3]


class VisibilityTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT/'tmp/age/pass9'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='visibility-test-')
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        labels = np.zeros((4, 4, 3), dtype=np.uint8)
        labels[0, 0] = (0, 255, 0)
        labels[1, 1] = (0, 0, 255)
        Image.fromarray(labels).save(self.out/'hero-visibility.png')
        after = np.full((4, 4, 3), 100, dtype=np.uint8)
        Image.fromarray(after).save(self.out/'sofa-after.png')
        for name in [*ORDER, 'Throw']:
            folder = self.out/'diagnostics'/name
            folder.mkdir(parents=True)
            Image.fromarray(labels).save(folder/'labels.png')
        for name, pixel in [('fringe', (0, 0)), ('crumbs', (1, 1))]:
            control = after.copy()
            control[pixel] -= 8
            Image.fromarray(control).save(self.out/('hero-without-'+name+'.png'))

    def test_counts_only_visible_effects_with_lit_contrast(self):
        result = visibility(self.out)
        for name in ['fringe', 'crumbs']:
            self.assertEqual(result[name]['hero_first_hit_pixels'], 1)
            self.assertEqual(result[name]['lit_first_hit_pixels_changed_by_at_least_8_levels'], 1)
            self.assertTrue(result[name]['pass'])

    def test_seat_front_cyan_counts_as_crumbs_and_not_fringe(self):
        labels = np.array(Image.open(self.out/'hero-visibility.png'))
        labels[1, 1] = (0, 255, 255)
        Image.fromarray(labels).save(self.out/'hero-visibility.png')
        result = visibility(self.out)
        self.assertEqual(result['crumbs']['seat_front_first_hit_pixels'], 1)
        self.assertEqual(result['crumbs']['lit_seat_front_pixels_changed_by_at_least_8_levels'], 1)
        self.assertEqual(result['fringe']['hero_first_hit_pixels'], 1)

    def test_diagnostic_presence_without_lit_contrast_fails(self):
        control = np.full((4, 4, 3), 100, dtype=np.uint8)
        control[0, 0] -= 7
        Image.fromarray(control).save(self.out/'hero-without-fringe.png')
        self.assertFalse(visibility(self.out)['fringe']['pass'])

    def test_lit_change_away_from_the_effect_does_not_prove_visibility(self):
        control = np.full((4, 4, 3), 100, dtype=np.uint8)
        control[3, 3] -= 20
        Image.fromarray(control).save(self.out/'hero-without-fringe.png')
        self.assertFalse(visibility(self.out)['fringe']['pass'])


class FrontFoldTests(unittest.TestCase):
    def test_edge_on_panels_have_zero_front_folds(self):
        import trimesh
        from sofa_decay_measure import front_folds
        vertices = [(x, y, z) for x in [-.5, .5] for y, z in [(0, 0), (.1, 0), (.1, .2), (0, .2)]]
        mesh = trimesh.Trimesh(vertices, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)], process=False)
        result = front_folds(mesh)
        self.assertEqual(result['folds'], 0)
        self.assertEqual(result['profile_counts'], [0]*5)


if __name__ == '__main__':
    unittest.main()
