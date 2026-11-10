"""Construction regressions for thin bevels and closed leather seam loops."""
import math
from pathlib import Path
import sys
import unittest

import bmesh

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


class ConstructionTests(unittest.TestCase):
    def setUp(self):
        sc.bt.reset()
        self.material=sc.bt.material('Test',(.5,.5,.5,1))

    def test_closed_horizontal_seam(self):
        centers=[(.05*math.cos(i*math.tau/24),.06*math.sin(i*math.tau/24),.2) for i in range(24)]
        obj=sc.tube('Seam',centers,.001,self.material,5,closed=True,frame_axis=(0,0,1))
        mesh=bmesh.new();mesh.from_mesh(obj.data)
        self.assertTrue(all(edge.is_manifold for edge in mesh.edges))
        self.assertTrue(all(face.calc_area()>1e-12 for face in mesh.faces))
        self.assertGreater(mesh.calc_volume(signed=True),0)
        mesh.free()

    def test_parallel_frame_fails(self):
        with self.assertRaises(AssertionError):
            sc.tube('BadFrame',[(0,0,0),(0,.1,0)],.001,self.material)

    def test_thin_panel_bevel_fails(self):
        with self.assertRaises(AssertionError):
            sc.box('Collapsed',(.1,.1,.002),(0,0,0),self.material,.001)

    def test_small_panel_remains_closed(self):
        obj=sc.box('Screen',(.1,.1,.002),(0,0,0),self.material,.0004)
        mesh=bmesh.new();mesh.from_mesh(obj.data)
        self.assertTrue(all(edge.is_manifold for edge in mesh.edges))
        self.assertTrue(all(face.calc_area()>1e-12 for face in mesh.faces))
        mesh.free()


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ConstructionTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
