"""Small die variation keeps the generated star within its normal-tilt limit."""
import unittest
import numpy as np
from medal_twelfth_finish import tilt_planes, normalized_photo, ribbon_field


class TwelfthFinishTests(unittest.TestCase):
    def test_tilts_are_bounded_and_unit_length(self):
        planes=np.tile([0.,-1.,0.],(10,1))
        detail=np.arange(20,dtype=float).reshape(10,2)-10
        varied=tilt_planes(planes,detail,.8)
        angles=np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',planes,varied),-1,1)))
        self.assertLessEqual(angles.max(),.800001)
        self.assertGreater(angles.std(),.01)
        np.testing.assert_allclose(np.linalg.norm(varied,axis=1),1)
        self.assertTrue((varied[:,1]<0).all())

    def test_flat_photo_rejected_instead_of_fabricating_detail(self):
        with self.assertRaises(ValueError):normalized_photo(np.ones((16,16)))

    def test_ribbon_field_reduces_bands_without_removing_rib_frequency(self):
        y,x=np.indices((512,512));photo=np.cos(y*2*np.pi*13/512)+.8*np.sin(x*.11+y*.15)
        field=ribbon_field(photo)
        row=field.mean(1)
        self.assertLess(row.std(),photo.mean(1).std()*.5)
        self.assertGreater(abs(np.fft.rfft(row))[13],1.)
        self.assertGreater(field.std(),.1)


if __name__=='__main__':unittest.main()
