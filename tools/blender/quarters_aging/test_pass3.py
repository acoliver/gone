"""Controls for camera-visibility and actual movement gates."""
import unittest

import numpy as np
import trimesh

from pass3_gates import area_centroid, raster, rectangle_rms, sleeve_pose


class CameraVisibility(unittest.TestCase):
    def test_first_hit_hides_farther_target(self):
        p=np.array([[-.4,-.4,0],[.4,-.4,0],[.4,.4,0],[-.4,.4,0]])
        back=trimesh.Trimesh(p,[[0,1,2],[0,2,3]],process=False)
        front=back.copy();front.vertices[:,2]=1
        ids=raster([(back,1),(front,2)],np.array([0.,0.,3.]),np.zeros(3),1.2,80,80)
        self.assertGreater((ids==2).sum(),0)
        self.assertEqual((ids==1).sum(),0)

    def test_centroid_is_area_weighted(self):
        mesh=trimesh.Trimesh([[0,0,0],[3,0,0],[0,3,0],[9,0,0],[10,0,0],[9,1,0]],[[0,1,2],[3,4,5]],process=False)
        np.testing.assert_allclose(area_centroid(mesh),[1.8333333333,.9333333333,0])

    def test_sleeve_pose_uses_cuff_and_cap_pattern_islands(self):
        from types import SimpleNamespace
        points=np.array([[-.01,0,0],[.01,0,0],[-.01,-.5,0],[.01,-.5,0],[4,4,4]])
        uv=np.array([[1.2,0],[1.3,0],[1.2,1],[1.3,1],[1.8,1]])
        mesh=SimpleNamespace(vertices=points,visual=SimpleNamespace(uv=uv))
        centre,axis=sleeve_pose(mesh,1.1,1.55)
        np.testing.assert_allclose(centre,[0,-.5,0])
        np.testing.assert_allclose(axis,[0,-1,0])
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]])
        mesh.vertices=points@rotation.T+[.1,.2,.3]
        moved,turned=sleeve_pose(mesh,1.1,1.55)
        np.testing.assert_allclose(moved,[.6,.2,.3])
        np.testing.assert_allclose(turned,[1,0,0],atol=1e-12)
        mesh.vertices=np.vstack([mesh.vertices,[2,2,2]])
        mesh.visual.uv=np.vstack([uv,[1.25,1]])
        matched,matched_axis=sleeve_pose(mesh,1.1,1.55,reference_uv=uv)
        np.testing.assert_allclose(matched,[.6,.2,.3])
        np.testing.assert_allclose(matched_axis,[1,0,0],atol=1e-12)

    def test_rectangle_and_irregular_outline(self):
        t=np.linspace(-1,1,50)
        p=np.vstack([np.c_[t,np.ones(50)],np.c_[np.ones(50),t],np.c_[t,-np.ones(50)],np.c_[-np.ones(50),t]])
        self.assertLess(rectangle_rms(p),1e-5)
        p[:50,1]+=.06*np.sin(t*9)
        self.assertGreater(rectangle_rms(p),.012)


if __name__=='__main__': unittest.main()
