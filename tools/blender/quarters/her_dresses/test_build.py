"""Controls for dress seam placement, flat patterns and available hang space."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'her_jacket')]
from build import BAYS,RAIL_Y,pattern
import space
import silhouette


class DressConstructionTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_cap_sleeve_and_side_seams_start_within_three_mm(self):
        for index,config in enumerate(BAYS):
            obj,pairs,_=pattern(config,index)
            self.assertLessEqual(max((obj.data.vertices[a].co-obj.data.vertices[b].co).length for a,b in pairs),.003)

    def test_initial_plies_are_separate_and_triangles_have_area(self):
        for index,config in enumerate(BAYS):
            obj,_,_=pattern(config,index)
            obj.data.calc_loop_triangles()
            points=np.array([v.co[:] for v in obj.data.vertices])
            f=np.array([t.vertices[:] for t in obj.data.loop_triangles])
            triangles=points[f]
            area=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)/2
            self.assertGreater(float(area.min()),1e-10)
            front,back=np.split(points,2)
            same_height=np.abs(front[:,2]-back[:,2])<1e-7
            self.assertTrue(np.all(back[same_height,0]-front[same_height,0]>.0005))

    def test_retained_cut_patterns_are_flat(self):
        for index,config in enumerate(BAYS):
            pattern(config,index)
            source=bpy.data.objects[config['name']+'_CutPattern']
            front,back=np.split(np.array([v.co[:] for v in source.data.vertices]),2)
            self.assertLess(float(np.ptp(front[:,0])),1e-7)
            self.assertLess(float(np.ptp(back[:,0])),1e-7)

    def test_flat_pattern_normals_point_out_of_the_garment(self):
        for index,config in enumerate(BAYS):
            pattern(config,index)
            source=bpy.data.objects[config['name']+'_CutPattern']
            source.data.update()
            first,second=np.split(np.array([p.normal.x for p in source.data.polygons]),2)
            self.assertTrue(np.all(first<-.99))
            self.assertTrue(np.all(second>.99))

    def test_silhouette_fit_keeps_stitches_and_is_repeatable(self):
        obj,_,pins=pattern(BAYS[0],0)
        group=obj.vertex_groups.new(name='SupportStitches')
        group.add(list(pins),1.,'REPLACE')
        locked={i:obj.data.vertices[i].co.copy() for i in pins}
        for v in obj.data.vertices:
            if v.index not in pins:v.co.y*=.3;v.co.z+=.12
        silhouette.fit(obj,RAIL_Y)
        first=np.array([v.co[:] for v in obj.data.vertices])
        silhouette.fit(obj,RAIL_Y)
        self.assertTrue(np.allclose(first,np.array([v.co[:] for v in obj.data.vertices]),atol=1e-7))
        self.assertTrue(all((obj.data.vertices[i].co-p).length<1e-7 for i,p in locked.items()))
        hem=first[first[:,2]<.51]
        self.assertGreater(float(np.ptp(hem[:,1])),.4)

    def test_aged_fit_preserves_most_of_the_simulated_sag(self):
        obj,_,pins=pattern(BAYS[0],0)
        group=obj.vertex_groups.new(name='SupportStitches')
        group.add(list(pins),1.,'REPLACE')
        original={v.index:float(v.co.z) for v in obj.data.vertices}
        for v in obj.data.vertices:
            if v.index not in pins:v.co.z-=.10
        silhouette.fit(obj,RAIL_Y,aged=True)
        drop=[original[v.index]-v.co.z for v in obj.data.vertices if v.index not in pins]
        self.assertGreater(float(np.mean(drop)),.065)

    def test_initial_cloth_hangs_below_its_hanger_not_the_free_bay_centre(self):
        for index,config in enumerate(BAYS):
            obj,_,_=pattern(config,index)
            points=np.array([v.co[:] for v in obj.data.vertices])
            lower=points[points[:,2]<1.4]
            self.assertLess(float(np.abs(lower[:,0]-config['x']).max()),.023)
            self.assertAlmostEqual(float(points[:,0].mean()),config['x'],places=5)

    def test_tunic_sleeves_do_not_flatten_the_whole_dress_bay(self):
        for left in (True,False):
            def width(z):
                a,b=space.bounds_at(z,left)
                return b-a
            self.assertGreater(width(1.55),width(1.20)+.04)
            self.assertGreater(width(.55),width(1.20)+.10)


if __name__=='__main__':
    result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(DressConstructionTests))
    if not result.wasSuccessful():raise SystemExit(1)
