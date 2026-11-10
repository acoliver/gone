"""Acceptance must use complete views, current numeric gates and matched scores."""
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from review_library import ROOT, VIEWS, BASE_RATINGS, acceptance, archive_review, compose_review


def report(aged=7, locker=7, legacy=6):
    scores = {key: dict(score=7) for key in BASE_RATINGS}
    scores['candidate_aged']['score'] = aged
    scores['locker_aged']['score'] = locker
    scores.update(legacy_as_built=dict(score=7), legacy_aged=dict(score=legacy))
    return dict(ratings=scores, images_seen=list(VIEWS))


class ReviewContractTests(unittest.TestCase):
    def test_acceptance_requires_score_scope_and_numeric_gates(self):
        self.assertTrue(acceptance(report(), 'desk', 0)['accepted'])
        self.assertFalse(acceptance(report(aged=6), 'desk', 0)['accepted'])
        self.assertFalse(acceptance(report(), 'desk', 1)['accepted'])
        incomplete = report(aged=9)
        incomplete['images_seen'] = ['hero', 'front']
        self.assertFalse(acceptance(incomplete, 'desk', 0)['accepted'])

    def test_wardrobe_must_also_equal_its_per_face_finish(self):
        self.assertFalse(acceptance(report(aged=7, legacy=8), 'wardrobe', 0)['accepted'])
        self.assertTrue(acceptance(report(aged=8, legacy=8), 'wardrobe', 0)['accepted'])

    def test_invalid_external_scores_fail_visibly(self):
        for invalid in (11, '7', True, float('nan')):
            with self.assertRaises(ValueError):
                acceptance(report(aged=invalid), 'desk', 0)

    def test_archive_keeps_the_actual_review_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/mat2') as name:
            directory = Path(name)
            for filename in ('material-review.json', 'review-response.json', 'review-prompt.txt', 'matched-review.png'):
                (directory/filename).write_bytes(filename.encode())
            archive_review(directory)
            for filename in ('material-review.json', 'review-response.json', 'review-prompt.txt', 'matched-review.png'):
                self.assertEqual((directory/'history/1'/filename).read_bytes(), filename.encode())
            self.assertFalse((directory/'material-review.json').exists())
            self.assertTrue((directory/'matched-review.png').exists())

    def test_unchanged_matched_pixels_keep_their_review_and_changed_pixels_archive_it(self):
        from library_gates import compose
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/mat2') as name:
            directory = Path(name)
            render, output = directory/'render', directory/'review'
            render.mkdir()
            output.mkdir()
            for view in VIEWS:
                for identity in ('desk', 'locker'):
                    for state in ('as_built', 'aged'):
                        Image.new('RGB', (16, 16), (90, 100, 95)).save(render/f'desk-{identity}-{state}-{view}.png')
            compose('desk', render, output)
            (output/'review-response.json').write_text('original response')
            (output/'material-review.json').write_text('original rating')
            compose('desk', render, output)
            self.assertEqual((output/'material-review.json').read_text(), 'original rating')
            self.assertFalse((output/'history').exists())
            Image.new('RGB', (16, 16), (120, 40, 20)).save(render/'desk-desk-aged-hero.png')
            compose('desk', render, output)
            self.assertFalse((output/'material-review.json').exists())
            self.assertEqual((output/'history/1/material-review.json').read_text(), 'original rating')
            self.assertTrue((output/'history/1/matched-hero.png').exists())

    def test_wardrobe_composite_contains_all_states_and_comparators(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/mat2') as name:
            directory = Path(name)
            render = directory/'render'
            render.mkdir()
            for vi, view in enumerate(VIEWS):
                for ci, identity in enumerate(('wardrobe', 'legacy', 'locker')):
                    for ri, state in enumerate(('as_built', 'aged')):
                        Image.new('RGB', (1024, 1024), (40+vi*40, 40+ci*60, 40+ri*100)).save(
                            render/f'wardrobe-{identity}-{state}-{view}.png')
            image = Image.open(compose_review('wardrobe', directory, render))
            self.assertEqual(image.size, (3072, 2144))
            for vi, view in enumerate(VIEWS):
                for ci in range(3):
                    for ri in range(2):
                        pixel = image.getpixel(((vi%2)*1536+ci*512+256,
                                                (vi//2)*1072+48+ri*512+256))
                        self.assertEqual(pixel, (40+vi*40, 40+ci*60, 40+ri*100))


if __name__ == '__main__':
    unittest.main()
