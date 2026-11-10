"""Visible panel outlines cannot bypass the retained seam gape/fringe checks."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_pass11_accept import tear_result


class TearAcceptanceTests(unittest.TestCase):
    def test_straight_run_success_does_not_override_failed_seam(self):
        result = tear_result([{'longest_straight_run_px': 5}],
                             {'seam_fringe_and_gape_pass': False, 'seam_gape_fraction': .1})
        self.assertFalse(result['pass'])
        self.assertFalse(result['seam_fringe_and_gape_pass'])

    def test_passing_visible_tears_keep_passing_seam_report(self):
        result = tear_result([{'longest_straight_run_px': 12}],
                             {'seam_fringe_and_gape_pass': True, 'seam_gape_fraction': .4})
        self.assertTrue(result['pass'])
        self.assertEqual(result['seam_gape_fraction'], .4)

    def test_missing_opening_fails_even_with_passing_seams(self):
        self.assertFalse(tear_result([], {'seam_fringe_and_gape_pass': True})['pass'])

    def test_throw_has_no_seam_exemption(self):
        self.assertFalse(tear_result([{'longest_straight_run_px': 13}], None)['pass'])


if __name__ == '__main__':
    unittest.main()
