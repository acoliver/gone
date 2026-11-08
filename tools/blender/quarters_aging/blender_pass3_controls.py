"""Run with Blender --background --python-exit-code 1 --python <this file>."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from collision_export import topology
from common import assert_collision_clear, assert_surface_clear, collision, settle
from detail_fit import fit_patch, trim_fold_contacts
from fabric_mesh import fray, material, new_object
from stress_cut import cut_faces


class ClothInputControls(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.mat=material('Control',(.3,.3,.3))

    def test_crossed_initial_triangles_are_rejected(self):
        obj=new_object('Crossed',[[0,0,0],[1,0,0],[0,1,0],[.2,-.2,-1],[.2,-.2,1],[.2,1.2,0]],[[0,1,2],[3,4,5]],self.mat)
        with self.assertRaisesRegex(ValueError,'cross before simulation'):
            assert_surface_clear(obj)

    def test_clear_initial_triangles_are_accepted(self):
        obj=new_object('Clear',[[0,0,0],[1,0,0],[0,1,0],[0,0,.1],[1,0,.1],[0,1,.1]],[[0,1,2],[3,4,5]],self.mat)
        assert_surface_clear(obj)

    def test_zero_pressure_disables_volume_preservation(self):
        obj=new_object('Cloth',[[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],self.mat)
        settings={'quality':1,'frames':1,'time_scale':.15,'mass':.12,'stiffness':180,'bending':.08}
        result=settle(obj,settings,{},pressure=0)
        self.assertFalse(result['pressure']['enabled'])
        self.assertEqual(result['pressure']['uniform_force'],0)

    def test_nonzero_pressure_remains_available_for_explicit_trials(self):
        obj=new_object('Cloth',[[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],self.mat)
        settings={'quality':1,'frames':1,'time_scale':.15,'mass':.12,'stiffness':180,'bending':.08}
        result=settle(obj,settings,{},pressure=2)
        self.assertTrue(result['pressure']['enabled'])
        self.assertEqual(result['pressure']['uniform_force'],2)

    def test_initial_collider_crossing_is_rejected(self):
        obj=new_object('Cloth',[[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],self.mat)
        support=new_object('Support',[[.2,-.2,-1],[.2,-.2,1],[.2,1.2,0]],[[0,1,2]],self.mat)
        collision(support)
        with self.assertRaisesRegex(ValueError,'Cloth/Support: initial triangles'):
            assert_collision_clear(obj)

    def test_clear_initial_collider_is_accepted(self):
        obj=new_object('Cloth',[[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],self.mat)
        support=new_object('Support',[[0,0,-.1],[1,0,-.1],[0,1,-.1]],[[0,1,2]],self.mat)
        collision(support)
        assert_collision_clear(obj)

    def test_point_contact_is_split_into_two_open_cloth_fans(self):
        obj=new_object('PointContact',[[0,0,0],[1,0,0],[1,1,0],[0,1,0],[-1,0,0],[-1,-1,0],[0,-1,0]],[[0,1,2,3],[0,4,5,6]],self.mat)
        cut_faces(obj,lambda p:False,95,refine=False)
        obj.data.calc_loop_triangles()
        vertices=np.array([v.co[:] for v in obj.data.vertices])
        faces=np.array([t.vertices[:] for t in obj.data.loop_triangles])
        result=topology(vertices,faces)
        self.assertTrue(result['unbranched_boundaries'])
        self.assertEqual(len(result['boundary_loops']),2)
        assert_surface_clear(obj)

    def test_reinforcement_uses_lifted_support_triangles(self):
        body=new_object('Support',[[0,0,0],[1,0,.2],[1,1,.2],[0,1,0]],[[0,1,2],[0,2,3]],self.mat)
        points=[[.2,.2,.5],[.8,.2,.5],[.8,.8,.5],[.2,.8,.5]]
        patch=new_object('Patch',points,[[0,1,2,3]],self.mat)
        fit_patch(patch,body,points,upward=True)
        p=np.array([v.co[:] for v in patch.data.vertices])
        np.testing.assert_allclose(p[:,2]-.2*p[:,0],.003,atol=1e-7)
        np.testing.assert_allclose(p[:,:2].min(0),[.2,.2],atol=1e-7)
        np.testing.assert_allclose(p[:,:2].max(0),[.8,.8],atol=1e-7)
        assert_surface_clear(patch)

    def test_fray_keeps_base_triangles_nondegenerate(self):
        obj=new_object('Cloth',[[.1964602917432785,-.027297865599393845,-.23634372651576996],[.201059952378273,-.02418925054371357,-.23158584535121918],[.19560402631759644,-.028649872168898582,-.23366598784923553]],[[0,1,2]],self.mat)
        fray(obj,9501,probability=1,length=(.004,.009),max_edge=.03)
        obj.data.calc_loop_triangles()
        p=np.array([v.co[:] for v in obj.data.vertices])
        areas=[np.linalg.norm(np.cross(p[t.vertices[1]]-p[t.vertices[0]],p[t.vertices[2]]-p[t.vertices[0]]))/2 for t in obj.data.loop_triangles]
        self.assertGreater(min(areas),1e-10)

    def test_hem_boundary_keeps_its_kind_after_slumping(self):
        vertices=np.array([[0,0,-.35],[.4,0,-.35],[.4,0,-.4],[0,0,-.4]])
        faces=np.array([[0,1,2],[0,2,3]])
        uv=np.array([[[0,0],[1,0],[1,.02]],[[0,0],[1,.02],[0,.02]]])
        result=topology(vertices,faces,uv)
        self.assertEqual(result['boundary_loops'][0]['kind'],'hem')

    def test_patch_trim_removes_only_facets_crossing_a_fold(self):
        body=new_object('Fold',[[-.4,-1,-1],[-.4,1,-1],[-.4,0,1]],[[0,1,2]],self.mat)
        patch=new_object('Patch',[[-.6,-.2,0],[-.2,-.2,0],[-.2,.2,0],[-.6,.2,0],
                                  [.2,-.2,0],[.6,-.2,0],[.6,.2,0],[.2,.2,0]],
                         [[0,1,2,3],[4,5,6,7]],self.mat)
        result=trim_fold_contacts(patch,body)
        self.assertEqual(result['removed_contact_triangles'],2)
        self.assertEqual(len(patch.data.polygons),2)
        self.assertGreaterEqual(min(v.co.x for v in patch.data.vertices),.19)
        assert_surface_clear(patch)


if __name__=='__main__':
    result=unittest.main(argv=['blender-pass3-controls'],exit=False).result
    if not result.wasSuccessful():raise SystemExit(1)
