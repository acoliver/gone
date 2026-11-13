"""Photo detail retains measured texture without carrying the reference light gradient."""
import unittest
import numpy as np
from medal_eighth_finish import delight, tileable, normal_from_height


class PhotoDetailTests(unittest.TestCase):
    def test_divide_removes_constant_illumination_scale(self):
        y,x=np.mgrid[:64,:64]
        photo=(.4+.04*np.sin(x*.8))*(.7+y/180)
        np.testing.assert_allclose(delight(photo,8),delight(photo*.6,8),atol=1e-12)

    def test_detail_is_tileable_on_both_boundaries(self):
        y,x=np.mgrid[:10,:10]
        image=np.sin(x*1.7)*.1+np.cos(y*1.2)*.1+x*.01+y*.03
        result=tileable(image)
        np.testing.assert_allclose(result[0],result[-1],atol=1e-12)
        np.testing.assert_allclose(result[:,0],result[:,-1],atol=1e-12)
        self.assertGreater(result.std(),.01)

    def test_flat_detail_is_a_unit_normal(self):
        normals=normal_from_height(np.zeros((16,16)),2)
        np.testing.assert_allclose(normals,np.broadcast_to([0,0,1],normals.shape))
        np.testing.assert_allclose(np.linalg.norm(normals,axis=2),1)


if __name__=='__main__':
    unittest.main()
