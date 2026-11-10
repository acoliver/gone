"""Positive and negative controls for the clothing export gates."""
import unittest

import numpy as np
import trimesh

from verify import crossings, near_gap, support_pass


class ClothingGateTests(unittest.TestCase):
    def test_crossing_triangle_is_rejected(self):
        a=trimesh.Trimesh([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],process=False)
        b=trimesh.Trimesh([[.2,.2,-1],[.2,.2,1],[.8,.2,0]],[[0,1,2]],process=False)
        self.assertGreater(crossings(a,b),0)

    def test_coplanar_overlap_is_rejected(self):
        a=trimesh.Trimesh([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],process=False)
        self.assertEqual(crossings(a,a.copy()),1)

    def test_separated_triangles_are_clear(self):
        a=trimesh.Trimesh([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],process=False)
        b=a.copy();b.vertices[:,2]+=.001
        self.assertEqual(crossings(a,b),0)

    def test_support_limit_includes_three_mm(self):
        self.assertTrue(support_pass({'shoulder':.003}))

    def test_floating_support_is_rejected(self):
        self.assertFalse(support_pass({'shoulder':.00301}))

    def test_missing_support_is_rejected(self):
        self.assertFalse(support_pass({}))

    def test_gap_measures_triangle_interior(self):
        support=trimesh.Trimesh([[-1,0,-1],[1,0,-1],[0,0,1]],[[0,1,2]],process=False)
        cloth=trimesh.Trimesh([[-.1,.002,-.1],[.1,.002,-.1],[0,.002,.1]],[[0,1,2]],process=False)
        self.assertAlmostEqual(near_gap(cloth,support),.002,places=8)


if __name__=='__main__':unittest.main()
