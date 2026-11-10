"""Positive and negative controls for rigid-prop closure and UV gates."""
import unittest

import numpy as np
import trimesh

from verify_common import closure, uv_report, visibility


class ExportChecks(unittest.TestCase):
    def test_closed_box_passes(self):
        self.assertTrue(closure(trimesh.creation.box())['pass'])

    def test_missing_face_fails_rays(self):
        mesh=trimesh.creation.box()
        mesh.update_faces(mesh.face_normals[:,0]<.9)
        result=closure(mesh)
        self.assertFalse(result['pass'])
        self.assertGreater(result['missed_rays'],0)

    def test_reversed_shell_fails(self):
        mesh=trimesh.creation.box()
        mesh.invert()
        self.assertFalse(closure(mesh)['pass'])

    def test_visible_detail_passes(self):
        mesh=trimesh.creation.box()
        report=visibility({'detail':mesh},mesh,np.array([0,0,3.]),['detail'])
        self.assertTrue(report['detail']['pass'])

    def test_occluded_detail_fails(self):
        mesh=trimesh.creation.box()
        blocker=trimesh.creation.box(extents=[2,2,.1])
        blocker.apply_translation([0,0,1])
        combined=trimesh.util.concatenate([mesh,blocker])
        report=visibility({'detail':mesh,'blocker':blocker},combined,np.array([0,0,3.]),['detail'])
        self.assertFalse(report['detail']['pass'])
    def test_orthographic_occlusion_uses_parallel_rays(self):
        detail=trimesh.creation.box(extents=[.2,.2,.2])
        detail.apply_translation([1,0,0])
        blocker=trimesh.creation.box(extents=[.3,.3,.1])
        blocker.apply_translation([1,0,1])
        meshes={'detail':detail,'blocker':blocker}
        combined=trimesh.util.concatenate(list(meshes.values()))
        camera=np.array([0,0,3.])
        perspective=visibility(meshes,combined,camera,['detail'])
        orthographic=visibility(meshes,combined,camera,['detail'],
                                orthographic_target=np.zeros(3))
        self.assertTrue(perspective['detail']['pass'])
        self.assertFalse(orthographic['detail']['pass'])


    def uv_mesh(self,coordinates):
        mesh=trimesh.Trimesh(
            vertices=[[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1,0,1],[0,1,1]],
            faces=[[0,1,2],[3,4,5]])
        mesh.visual=trimesh.visual.texture.TextureVisuals(uv=np.array(coordinates))
        return mesh

    def test_overlapping_uvs_fail(self):
        mesh=self.uv_mesh([[0,0],[1,0],[0,1]]*2)
        self.assertFalse(uv_report({'test':mesh})['pass'])

    def test_equal_density_disjoint_uvs_pass(self):
        mesh=self.uv_mesh([[0,0],[.4,0],[0,.4],[.6,.6],[1,.6],[.6,1]])
        self.assertTrue(uv_report({'test':mesh})['pass'])


if __name__=='__main__':
    unittest.main()
