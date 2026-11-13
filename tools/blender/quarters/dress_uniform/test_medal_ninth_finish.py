"""Material detail follows measured physical scale and keeps exposed brass clean."""
import unittest
import numpy as np
from medal_ninth_finish import fine_rib_cycles, cavity_oxide, restrict_facet_detail


class NinthFinishTests(unittest.TestCase):
    def test_fine_rib_measurement_rejects_broad_stripe(self):
        y=np.arange(120)
        photo=np.repeat((.3*np.cos(y*2*np.pi/12)+.06*np.cos(y*2*np.pi/4))[:,None],40,1)
        self.assertAlmostEqual(fine_rib_cycles(photo),30,delta=.5)

    def test_oxide_requires_cavity_and_rejects_exposed_face(self):
        concave=np.array([0,.8,.8]);convex=np.array([0,0,.8]);ao=np.array([1,.35,.35]);photo=np.array([.2,.2,.2])
        values=cavity_oxide(concave,convex,ao,photo)
        self.assertEqual(values[0],0)
        self.assertGreater(values[1],.5)
        self.assertLess(values[2],values[1]*.05)

    def test_photo_detail_does_not_warp_facet_planes(self):
        current=np.array([[[.3,.1,.95],[.2,.2,.96]]]);flat=np.array([[[0,0,1],[.1,0,.995]]]);mask=np.array([[True,False]])
        result=restrict_facet_detail(current,flat,mask)
        np.testing.assert_array_equal(result[0,0],flat[0,0])
        np.testing.assert_array_equal(result[0,1],current[0,1])


if __name__=='__main__':unittest.main()
