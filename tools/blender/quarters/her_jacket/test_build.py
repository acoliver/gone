"""Blender controls for the cloth pin rows and wire frame construction."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build import pattern
from cloth_tools import tube


def triangle_areas(obj):
    obj.data.calc_loop_triangles()
    p=np.array([v.co[:] for v in obj.data.vertices])
    f=np.array([t.vertices[:] for t in obj.data.loop_triangles])
    t=p[f]
    return np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2


class ConstructionTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_posed_jacket_has_no_collapsed_faces(self):
        obj,_,pins=pattern()
        self.assertGreater(float(triangle_areas(obj).min()),1e-9)
        uv=obj.data.uv_layers.active.data
        rows={round(float(uv[l.index].uv.y)/8,4) for l in obj.data.loops if l.vertex_index in pins}
        self.assertEqual(rows,{.6})

    def test_symmetric_yz_wire_apex_has_finite_radius(self):
        obj=tube('TestHanger',[(0,-.1,1.67),(0,0,1.69),(0,.1,1.67)])
        self.assertGreater(float(triangle_areas(obj).min()),1e-9)
        middle=np.array([v.co[:] for v in obj.data.vertices])[8:16]
        radii=np.linalg.norm(middle-np.array([0,0,1.69]),axis=1)
        self.assertTrue(np.allclose(radii,.0025,atol=1e-7))


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ConstructionTests)
    result=unittest.TextTestRunner().run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
