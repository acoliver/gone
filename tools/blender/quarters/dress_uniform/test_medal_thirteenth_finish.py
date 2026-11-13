"""Struck-facet curvature is bounded and vanishes at the retained die edges."""
import unittest
import numpy as np
from medal_thirteenth_finish import pillow_slopes


class ThirteenthFinishTests(unittest.TestCase):
    def test_curvature_preserves_radial_and_outline_boundaries(self):
        r=np.linspace(.001,.009,60)
        p=np.c_[np.zeros_like(r),r]
        np.testing.assert_allclose(pillow_slopes(p,.010,3),0,atol=1e-14)
        a=np.linspace(.01,np.pi/5-.01,60)
        p=.010*np.c_[np.sin(a),np.cos(a)]
        np.testing.assert_allclose(pillow_slopes(p,.010,3),0,atol=1e-14)

    def test_peak_tilt_bounded_and_not_a_constant_plane(self):
        r,a=np.meshgrid(np.linspace(.00001,.00999,180),np.linspace(.00001,np.pi/5-.00001,180))
        p=np.stack([r*np.sin(a),r*np.cos(a)],axis=-1)
        slopes=pillow_slopes(p,.010,3)
        tilt=np.degrees(np.arctan(np.linalg.norm(slopes,axis=-1)))
        self.assertLessEqual(tilt.max(),3.00001)
        self.assertGreater(tilt.max(),2.)
        self.assertGreater(tilt.std(),.3)
        self.assertLess(np.linalg.norm(slopes.mean(axis=(0,1))),.003)

    def test_identical_curvature_after_rotating_one_facet(self):
        a=np.linspace(.03,.59,30);p=.005*np.c_[np.sin(a),np.cos(a)]
        t=np.pi/5;rotation=np.array([[np.cos(t),np.sin(t)],[-np.sin(t),np.cos(t)]])
        np.testing.assert_allclose(pillow_slopes(p@rotation.T,.010,3),pillow_slopes(p,.010,3)@rotation.T,atol=1e-12)

    def test_invalid_dimensions_fail(self):
        with self.assertRaises(ValueError):pillow_slopes(np.array([[0.,.005]]),0,3)
        with self.assertRaises(ValueError):pillow_slopes(np.array([[0.,.005]]),.010,-1)


if __name__=='__main__':unittest.main()
