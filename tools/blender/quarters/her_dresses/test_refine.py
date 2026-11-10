"""Regression controls for coarse tear lips, locked supports and soft deposits."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'her_jacket')]
from cloth_tools import mesh
import refine


class DryFinishTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        refine.TEXTURES=HERE.parents[3]/'tmp/clothes2/test-textures'

    def test_coarse_hem_edges_gain_fine_grain_aligned_variation(self):
        obj=mesh('CoarseHem',[(-.1,0,.5),(0,0,.5),(.1,0,.54),(-.1,0,.65),(0,0,.65),(.1,0,.65)],
                 [(0,1,4,3),(1,2,5,4)])
        before=len(obj.data.vertices)
        refine.ragged_edges(obj)
        self.assertGreater(len(obj.data.vertices),before)
        lower=np.array([v.co[:] for v in obj.data.vertices if v.co.z<.60])
        self.assertGreater(float(np.ptp(lower[:,2])),.005)
        obj.data.calc_loop_triangles()
        self.assertTrue(all(t.area>1e-12 for t in obj.data.loop_triangles))

    def test_short_hem_segments_do_not_alias_into_deep_sawteeth(self):
        xs=np.linspace(-.25,.25,26)
        vertices=[(x,0,z) for z in (.5,1.1) for x in xs]
        obj=mesh('ShortHem',vertices,[(i,i+1,i+27,i+26) for i in range(25)])
        refine.ragged_edges(obj)
        lower=np.array([v.co[:] for v in obj.data.vertices if v.co.z<.60 and abs(v.co.x)<.03])
        self.assertLess(float(np.ptp(lower[:,2])),.004)
        self.assertGreater(float(np.ptp(lower[:,2])),.0002)

    def test_shoulder_tip_is_rounded_across_the_refinement_band_boundary(self):
        import bmesh
        import math
        obj=mesh('ShoulderTip',[(-.1,0,1.43),(0,0,1.55),(.1,0,1.43),(.1,0,1.67),(-.1,0,1.67)],[(0,1,2,3,4)])
        refine.ragged_edges(obj)
        bm=bmesh.new();bm.from_mesh(obj.data)
        turns=[]
        for vertex in bm.verts:
            edges=[e for e in vertex.link_edges if e.is_boundary]
            if len(edges)==2 and 1.51<vertex.co.z<1.62:
                a,b=[e.other_vert(vertex).co-vertex.co for e in edges]
                turns.append(180-math.degrees(a.angle(b)))
        bm.free()
        self.assertTrue(turns)
        self.assertLess(max(turns),60)

    def test_supported_shoulder_stitches_do_not_move(self):
        obj=mesh('Shoulder',[(-.1,0,1.60),(.1,0,1.60),(.1,0,1.65),(-.1,0,1.65)],[(0,1,2,3)])
        group=obj.vertex_groups.new(name='SupportStitches');group.add([2,3],1.,'REPLACE')
        before=[obj.data.vertices[i].co.copy() for i in (2,3)]
        refine.ragged_edges(obj)
        self.assertTrue(all(any((v.co-p).length<1e-7 for v in obj.data.vertices) for p in before))

    def test_fringe_has_explicit_opposite_faces_for_mirrored_room_lighting(self):
        obj=mesh('Card',[(0,0,0),(.01,0,0),(.01,0,.01),(0,0,.01)],[(0,1,2,3)])
        refine.reverse_faces(obj)
        refine.recalc(obj)
        self.assertEqual(len(obj.data.polygons),2)
        normals=np.array([p.normal[:] for p in obj.data.polygons])
        self.assertLess(float(normals[0]@normals[1]),-.99)

    def test_fringe_root_keeps_separate_strands_instead_of_an_opaque_strip(self):
        material=refine.fringe_material_for_dresses()
        shader=material.node_tree.nodes['Principled BSDF']
        image=shader.inputs['Base Color'].links[0].from_node.image
        alpha=np.asarray(image.pixels[:]).reshape(image.size[1],image.size[0],4)[:,:,3]
        coverage=float(np.mean(alpha[::256]>.5))
        self.assertGreater(coverage,.10)
        self.assertLess(coverage,.50)

    def test_powder_card_has_transparent_feathering_and_millimetre_support(self):
        obj=refine.powder('Test_FibreHeap',-.29,1)
        points=np.array([v.co[:] for v in obj.data.vertices])
        self.assertAlmostEqual(float(points[:,2].min()),.1448,places=6)
        mat=obj.data.materials[0]
        image=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and not n.image.name.endswith('Normal'))
        alpha=np.asarray(image.pixels[:]).reshape(-1,4)[:,3]
        self.assertGreater(float(np.mean(alpha==0)),.1)
        self.assertGreater(float(np.mean(alpha==1)),.1)

    def test_powder_core_retains_shelf_contact_and_game_scale_relief(self):
        card=refine.powder('Test_FibreHeap',-.29,1)
        core=refine.mound('Test_Core',card,-.29)
        points=np.array([v.co[:] for v in core.data.vertices])
        self.assertAlmostEqual(float(points[:,2].min()),.1448,places=6)
        self.assertGreater(float(np.ptp(points[:,2])),.022)
        self.assertLess(float(np.ptp(points[:,2])),.030)

    def test_stiffening_keeps_upper_support_band_fixed(self):
        obj=mesh('Fold',[(.035,-.11,1.1),(-.1,-.11,1.1),(0,-.11,1.66)],[(0,1,2)])
        before=np.asarray([v.co[:] for v in obj.data.vertices])
        record=refine.stiffen_folds(obj,0,0)
        after=np.asarray([v.co[:] for v in obj.data.vertices])
        np.testing.assert_array_equal(before[2],after[2])
        np.testing.assert_array_equal(before[:,[0,2]],after[:,[0,2]])
        self.assertGreater(record['maximum_displacement_m'],.001)

    def test_powder_clumps_are_repeatable_and_bounded(self):
        first=refine.clump_noise(64,95328)
        np.testing.assert_array_equal(first,refine.clump_noise(64,95328))
        self.assertGreaterEqual(float(first.min()),0)
        self.assertLessEqual(float(first.max()),1)
        self.assertGreater(float(np.std(first)),.05)

    def test_finish_restarts_from_unarranged_fitted_input(self):
        from dress_finish import restore_inputs
        obj=mesh('FittedDress',[(0,0,1.6),(.1,0,1.6),(0,0,1.7)],[(0,1,2)])
        original=np.asarray([v.co[:] for v in obj.data.vertices])
        restore_inputs()
        obj.data.vertices[0].co.x+=.17
        generated=mesh('TemporaryFringe',[(0,0,0),(.1,0,0),(0,0,.1)],[(0,1,2)])
        generated['finish_generated']=True
        restore_inputs()
        np.testing.assert_array_equal(np.asarray([v.co[:] for v in obj.data.vertices]),original)
        self.assertNotIn('TemporaryFringe',bpy.data.objects)
        self.assertFalse(bpy.data.objects['FittedDress_FinishInput']['aged_export'])


if __name__=='__main__':
    r=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(DryFinishTests))
    if not r.wasSuccessful():raise SystemExit(1)
