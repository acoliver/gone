"""Non-repeating photographic brass detail, without changing material calibration."""
import unittest
import numpy as np
from medal_tenth_finish import synthesize, periodicity


class TenthFinishTests(unittest.TestCase):
    def test_periodicity_detects_known_repetition(self):
        tile=np.random.default_rng(14).normal(size=(18,18))
        image=np.tile(tile,(24,24))
        result=periodicity(image,np.ones_like(image,dtype=bool),18/1.135)
        self.assertGreater(result['old_period_peak_correlation'],.9)
        self.assertAlmostEqual(result['dominant_period_mm'],1.135,delta=.12)

    def test_synthesis_has_no_repeated_patch_lattice(self):
        rng=np.random.default_rng(15)
        crops=[rng.normal(size=(31,31)) for _ in range(12)]
        first=synthesize(crops,512,seed=13010)
        np.testing.assert_array_equal(first,synthesize(crops,512,seed=13010))
        result=periodicity(first,np.ones_like(first,dtype=bool),16)
        self.assertLess(result['old_period_peak_correlation'],.2)
        self.assertLess(result['dominant_peak_correlation'],.3)
        self.assertTrue(np.isfinite(first).all())
        self.assertGreater(first.std(),.1)


if __name__=='__main__':unittest.main()
