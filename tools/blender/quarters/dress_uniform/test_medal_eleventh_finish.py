"""Physical edge rounding and photographic band rejection."""
import unittest
import numpy as np
from medal_eleventh_finish import rounded_facet_normals, remove_row_bands, material_padding


class EleventhFinishTests(unittest.TestCase):
    def test_rounding_is_local_to_physical_ridge(self):
        planes=np.tile([0.,-1.,0.],(10,1));planes[0]=[.2,-.98,0];planes[9]=[-.2,-.98,0]
        points=np.array([[0,0,.005],[.001,0,.005],[-.001,0,.005]])
        n=rounded_facet_normals(points,planes,.000065)
        self.assertAlmostEqual(n[0,0],0,places=6)
        self.assertGreater(n[1,0],.19)
        self.assertLess(n[2,0],-.19)
        np.testing.assert_allclose(np.linalg.norm(n,axis=1),1)

    def test_row_filter_keeps_fibres_and_removes_broad_marks(self):
        y,x=np.indices((256,128));a=np.cos(y*2*np.pi/32)+.2*np.cos(y*2*np.pi/4)+.1*np.sin(x*.7+y*.4)
        b=remove_row_bands(a,64)
        power=abs(np.fft.rfft(b.mean(1)))
        self.assertLess(power[8],power[64]*.01)
        self.assertGreater(b.std(),.1)

    def test_padding_never_pulls_another_material(self):
        values=np.zeros((7,7,3));values[:]=[1,1,0];values[3,3]=[0,0,1]
        mask=np.zeros((7,7),bool);mask[3,3]=True
        result=material_padding(values,mask)
        np.testing.assert_array_equal(result,np.broadcast_to([0,0,1],result.shape))


if __name__=='__main__':unittest.main()