"""Controls for the rail frame and independent garment support transforms."""
import unittest

import numpy as np

from arrange import FRONT_OFFSET,POSITIONS,RAIL_Y,WIDTH_SCALE,positions


class ArrangementTests(unittest.TestCase):
    def test_hook_stays_in_the_original_rail_wrapping_plane(self):
        for name,(old,new) in POSITIONS.items():
            hook=old+.026 if old<0 else old
            points=np.array([(hook,RAIL_Y+.0193,1.82),(hook,RAIL_Y,1.8393)])
            result=positions(points,name,hanger=True)
            self.assertTrue(np.allclose(result[:,0],new))
            self.assertTrue(np.allclose(result[:,1:],points[:,1:]))

    def test_garment_and_hanger_supports_share_the_transform(self):
        for name,(old,new) in POSITIONS.items():
            points=np.array([(old,RAIL_Y-.18,1.648),(old,RAIL_Y+.18,1.648)])
            garment=positions(points,name)
            hanger=positions(points,name,hanger=True)
            self.assertTrue(np.allclose(garment,hanger))
            self.assertAlmostEqual(float(np.ptp(hanger[:,0])),.36*WIDTH_SCALE)
            self.assertTrue(np.allclose(hanger[:,1],RAIL_Y-FRONT_OFFSET))

    def test_original_inputs_are_not_modified(self):
        points=np.array([[-.451,RAIL_Y,.5]])
        before=points.copy()
        first=positions(points,'RoseDress')
        second=positions(points,'RoseDress')
        self.assertTrue(np.array_equal(first,second))
        self.assertTrue(np.array_equal(points,before))


if __name__=='__main__':unittest.main()
